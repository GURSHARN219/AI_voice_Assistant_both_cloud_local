import customtkinter as ctk
import threading
import asyncio
from codes.gui import VoiceChatGUI


def run_asyncio_loop(loop):
    """Runs the asyncio event loop in a separate thread."""
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == "__main__":
    """
    Main entry point of the application.
    Initializes the asyncio event loop in a background thread
    and starts the main Tkinter GUI.
    """
    main_loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(
        target=run_asyncio_loop, args=(main_loop,), daemon=True
    )
    loop_thread.start()
    app = VoiceChatGUI(main_loop)
    app.mainloop()
