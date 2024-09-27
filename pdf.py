from dataclasses import dataclass
from enum import Enum

import pymupdf
import random
import io

from PIL import Image
import pytesseract
import Levenshtein

from server import LOGGER
from openapi import page_embeddings

@dataclass
class Page:
    PageNum: int
    Content: str
    Embedding = []

@dataclass
class Book:
    Author: str
    Title: str
    Len: int
    PDFPath: str
    PubYear: int = 2021
    IsOCR: bool = False
    Pages = []

class TextChoice(Enum):
    PDFCORRECT = 1
    OCRCORRECT = 2
    UNKNOWN = 3

def page2pil(page):
    pix = page.get_pixmap(matrix=pymupdf.Matrix(300/72, 300/72))
    img_data = pix.tobytes("jpg")
    return Image.open(io.BytesIO(img_data))

def complen(pdftextL, ocrtextL):
    diff = 2 * abs(pdftextL - ocrtextL) / (pdftextL + ocrtextL)
    if diff >= 0.1:
        if pdftextL > ocrtextL:
            return TextChoice.PDFCORRECT
        else:
            return TextChoice.OCRCORRECT
    return TextChoice.UNKNOWN

def assert_utf8(text):
    try:
        text.encode('utf-8').decode('utf-8')
        return True
    except UnicodeDecodeError:
        
        return False

def check_text_quality(text):
    if not assert_utf8(text):
        return False

    unwanted = ['\ufffd','�','□','\x00','\x0c']

    for pattern in unwanted:
        if pattern in text:
            LOGGER.info(f"Problematic pattern found: {pattern}")
            return False

    alphanumeric_ratio = sum(c.isalnum() for c in text) / len(text) if text else 0
    if alphanumeric_ratio < 0.5 and alphanumeric_ratio != 0: # 0 == empty page, no punishment
        LOGGER.info(f"Low alphanumeric ratio: {alphanumeric_ratio}")
        return False

    return True

def check_page_quality(rawpage):
    pdftext = rawpage.get_text()
    imgpage = page2pil(rawpage)
    ocrtext = pytesseract.image_to_string(imgpage)

    pdf_quality = check_text_quality(pdftext)
    ocr_quality = check_text_quality(ocrtext)

    if not pdf_quality and ocr_quality:
        return TextChoice.OCRCORRECT
    elif pdf_quality and not ocr_quality:
        return TextChoice.PDFCORRECT

    similarity = Levenshtein.ratio(pdftext, ocrtext)
    if similarity < 0.8:
        return TextChoice.OCRCORRECT if len(ocrtext) > len(pdftext) else TextChoice.PDFCORRECT
    
    return TextChoice.UNKNOWN

def sample_pages(doc, sample, n):
    LOGGER.info(f"Sampling {n} pages")

    ocr_count = 0
    pdf_count = 0

    for idx in sample:
        LOGGER.info(f"Checking Sample Page {idx}")
        rawpage = doc.load_page(idx)
        
        quality = check_page_quality(rawpage)
        if quality == TextChoice.OCRCORRECT:
            ocr_count += 1
        elif quality == TextChoice.PDFCORRECT:
            pdf_count += 1

        if ocr_count >= n // 2 or pdf_count >= n // 2:
            if ocr_count > pdf_count:
                LOGGER.debug("OCR is overwhelmingly better")
                return True
            else:
                LOGGER.debug("PDF is overwhelmingly better")
                return False

    # rather not use OCR if the difference is not significant
    return ocr_count - 1 > pdf_count + 1
    
def handlePDFRead(b, doc, client):
    for i, page in enumerate(doc):
        page_number= i + 1
        text = page.get_text() if not b.IsOCR else pytesseract.image_to_string(page2pil(page))
        p = Page(page_number, text)
        page_embeddings(p, client)
        b.Pages.append(p)

def handle_book(b: Book, client):
    doc = pymupdf.open(b.PDFPath)
    b.Len = len(doc)
    LOGGER.debug(f"Total Pages: {b.Len}")

    n_samples = b.Len // 20
    if n_samples < 1:
        n_samples = 1
    sample = random.sample(range(1, b.Len), n_samples)
    
    b.IsOCR = sample_pages(doc, sample, n_samples)
    LOGGER.info(f"IsOCR: {b.IsOCR}")

    handlePDFRead(b, doc, client)

    doc.close()
