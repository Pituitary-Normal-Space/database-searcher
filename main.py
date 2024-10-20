"""
This is the main file of the program. It fires up the UI and manages the interaction with the user.
"""

import tkinter as tk
from dotenv import load_dotenv
from tkinter import simpledialog, messagebox

import key_manager as km
from search import DBSearcher
from const import VALID_DATABASES

# Load environment variables from the .env file
load_dotenv()

# Check if the API keys are saved in the environment variables
api_keys = km.get_keys()

# Check if the user has entered the API keys
if not all(api_keys.values()):
    exit()

dbsearcher = DBSearcher(api_keys)


# Function to handle button click and display entered data
def submit():
    user_input = entry.get()
    result_df = dbsearcher.search(user_input)
    # Close the dialog box and create a new one asking for a filename to save the results
    # Close the main window
    root.destroy()
    # Ask the user for a filename to save the results
    filename = simpledialog.askstring(
        "DBSearcher: Save Results",
        "Enter a filename to save the results. No need to add any file extensions:",
    )
    if not filename:
        filename = "results"

    # If there is a .csv for example only get the root name
    filename = filename.split(".")[0]

    # Save the results to a CSV file
    result_df.to_csv(f"results/{filename}.csv")

    # Show a message box to the user
    messagebox.showinfo(
        "DBSearcher: Results Saved",
        f'The results have been saved to {filename}.csv in the "results" directory. Please run the program again to search for more queries.',
    )


# Create the main window
root = tk.Tk()
root.title(f"DBSearcher: Search {" and ".join(VALID_DATABASES)}")

# Add a label
label = tk.Label(root, text="Enter a search query in proper PubMed syntax:")
label.pack(pady=10)

# Add an entry field
entry = tk.Entry(root, width=100)
entry.pack(pady=5, padx=20)

# Add a button to submit
submit_button = tk.Button(root, text="Submit", command=submit)
submit_button.pack(pady=10)

# Run the main event loop
root.mainloop()
