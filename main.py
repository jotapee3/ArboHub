import customtkinter as ctk

from app.gui.windows.main_window import MainWindow


def main():
    ctk.set_appearance_mode("dark")

    MainWindow()


if __name__ == "__main__":
    main()