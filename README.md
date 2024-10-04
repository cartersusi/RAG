# Python Server

1. Send book

2. Split Pages

3. Detect if Text or OCR processing

If Text {

    Process All Text

    (async 1) Get All Embeddings
    (async 2) Get All Images

    (async 1.1) Send All Embeddings to bstore
    (async 2.2) Send All Images to bstore

    Result = {image_links: [], embedding_link: str}
}


If OCR {

    Get Image for Pages
        (async) Send Image to bstore
        (async) Image -> Text

    (async nw=openai_max) Get All Embeddings
    Send Embeddings to bstore
    
    Result = {image_links: [], embedding_link: str}
}
