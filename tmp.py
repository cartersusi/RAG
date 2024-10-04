import asyncio

async def get_all_embeddings():
    print("get_all_embeddings()")
    await asyncio.sleep(2.5)
    print("get_all_embeddings() done")
    return "embeddings"

async def get_all_images():
    print("get_all_images()")
    await asyncio.sleep(0.5)
    print("get_all_images() done")
    return "images"

async def send_all_embeddings(embeddings):
    print("send_all_embeddings()")
    await asyncio.sleep(0.5)
    print("send_all_embeddings() done")

async def send_all_images(images):
    print("send_all_images()")
    await asyncio.sleep(1)
    print("send_all_images() done")

async def process_embeddings():
    embeddings = await get_all_embeddings()
    await send_all_embeddings(embeddings)

async def process_images():
    images = await get_all_images()
    await send_all_images(images)

async def main():
    embeddings_task = asyncio.create_task(process_embeddings())
    images_task = asyncio.create_task(process_images())

    await asyncio.gather(embeddings_task, images_task)

if __name__ == "__main__":
    asyncio.run(main())