import asyncio
from tests.test_memory_store import test_save_and_load_project_state, test_get_last_messages


async def main():
    await test_save_and_load_project_state()
    await test_get_last_messages()


if __name__ == "__main__":
    asyncio.run(main())
    print("Memory store tests passed")
