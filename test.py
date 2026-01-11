import tkinter as tk

# Create main window
window = tk.Tk()
window.title("Hello Window")
window.geometry("200x100")

# Create a label (text inside the box)
label = tk.Label(window, text="Hello", font=("Arial", 16))
label.pack(expand=True)

# Run the window
window.mainloop()
