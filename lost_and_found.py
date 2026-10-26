import streamlit as st
from datetime import date
from pathlib import Path
from object import Item
import sqlite3
 

DB_PATH = Path(__file__).parent / "sqlite.db"
 
connect = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = connect.cursor()
 
# Create the tables only if they don't exist yet.
# "IF NOT EXISTS" means this NEVER deletes or overwrites existing data.
cursor.execute("""CREATE TABLE IF NOT EXISTS lost_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    category TEXT,
    brand TEXT,
    color TEXT,
    location_found TEXT,
    date_found TEXT,
    image BLOB
)""")
 
cursor.execute("""CREATE TABLE IF NOT EXISTS claims (
    item_id INTEGER,
    student_username TEXT,
    claim_date TEXT,
    status TEXT
)""")
connect.commit()
 
# ---------------- SESSION STATE ----------------
if "page" not in st.session_state:
    st.session_state.page = "login"  # remembers which screen user should see
 
if "role" not in st.session_state:  # Remembers the role
    st.session_state.role = ""
 
if "username" not in st.session_state:
    st.session_state.username = ""
 
if "flash" not in st.session_state:  # message that survives st.rerun()
    st.session_state.flash = ""
 
 
# ---------------- HELPERS ----------------
def flash(message):
    # st.success() right before st.rerun() disappears instantly,
    # so the message is saved and shown after the page reloads
    st.session_state.flash = message
 
 
def show_flash():
    if st.session_state.flash != "":
        st.success(st.session_state.flash)
        st.session_state.flash = ""
 
 
def logout_button():
    if st.sidebar.button("Log out"):
        st.session_state.page = "login"
        st.session_state.role = ""
        st.session_state.username = ""
        st.rerun()
 
 
def check_login(filename, username, password):
    # Returns True if "username,password" is a line in the file
    users = []
    with open(Path(__file__).parent / filename, "r") as myfile:
        for line in myfile:
            users.append(line.strip())
    return f"{username},{password}" in users  # The f lets you put variables inside of a string
 
 
# ---------------- LOGIN PAGE ----------------
def home_page():
 
    st.title("Welcome to Lincoln School's Lost and Found!")
 
    st.write("Select your role:")
 
    col1, col2, col3, col4, col5, col6 = st.columns(6)
 
    # Select a role feature
    with col1:
        if st.button("Admin"):
            st.session_state.role = "Admin"
 
    with col2:
        if st.button("Student"):
            st.session_state.role = "Student"
 
    if st.session_state.role == "":
        st.error("You must choose a role before logging in")
        return  # stop here until a role is chosen
 
    st.write(f"{st.session_state.role} login selected")
 
    # Text inputs that allow you to write the username and password in
    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password").strip()  # hides the characters
 
    # Login button
    if st.button("Login"):
        # Usernames and passwords will be administered by technology, how lincoln does with Microsoft.
        if st.session_state.role == "Admin":
            filename = "admin.txt"
            next_page = "admin"
        else:
            filename = "student.txt"
            next_page = "student"
 
        try:
            if check_login(filename, username, password):
                st.session_state.username = username
                st.session_state.page = next_page
                flash(f"Welcome {st.session_state.role}!")
                st.rerun()  # refresh the app and use a new page
            else:
                st.error("The username or password is incorrect")
 
        except FileNotFoundError:
            st.error(f"I could not find the file {filename}")
 
 
# ---------------- ADMIN PAGE ----------------
def admin_page():
 
    logout_button()
 
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
 
    if "show_claims" not in st.session_state:
        st.session_state.show_claims = False
 
    st.header("Admin Dashboard")
    show_flash()
 
    col1, col2 = st.columns(2)
 
    with col1:
        if st.button("Add lost item"):
            st.session_state.show_form = True
 
    with col2:
        if st.button("View Claim Requests"):
            st.session_state.show_claims = not st.session_state.show_claims
 
    # View all requests to claim an item
    if st.session_state.show_claims:
        st.subheader("Claim Requests")
 
        cursor.execute("SELECT * FROM claims")
        all_claims = cursor.fetchall()
 
        # Search claims by student name (linear search, ignores capitals and spaces)
        student_search = st.text_input("Search claims by student username:").strip().lower()
 
        claims = []
        for claim in all_claims:
            stored_name = (claim[1] or "").strip().lower()
            if student_search == "" or student_search in stored_name:
                claims.append(claim)
 
        if len(all_claims) == 0:
            st.write("No claim requests.")
 
        elif len(claims) == 0:
            st.write(f"No claims found for '{student_search}'.")
 
        else:
            for claim in claims:
                st.write(f"Item ID: {claim[0]}, Student: {claim[1]}, Claim Date: {claim[2]}, Status: {claim[3]}")
 
                col1, col2, col3 = st.columns(3)
 
                # Accept or deny a claim
                with col1:
                    if st.button("Accept", key=f"accept_{claim[0]}"):
                        cursor.execute("UPDATE claims SET status = 'Approved' WHERE item_id = ?", (claim[0],))
                        connect.commit()
                        flash("Claim approved!")
                        st.rerun()
 
                with col2:
                    if st.button("Reject", key=f"reject_{claim[0]}"):
                        cursor.execute("UPDATE claims SET status = 'Rejected' WHERE item_id = ?", (claim[0],))
                        connect.commit()
                        flash("Claim rejected")
                        st.rerun()
 
                with col3:
                    # FIX: before it was  == "Collected" or "Rejected"  which is always True
                    if claim[3] in ("Collected", "Rejected"):
                        if st.button("Delete Claim", key=f"delete_claim_{claim[0]}"):
                            cursor.execute("DELETE FROM claims WHERE item_id = ?", (claim[0],))
                            connect.commit()
                            flash("Claim deleted!")
                            st.rerun()
 
    # Form required to add a new item
    if st.session_state.show_form:
 
        with st.form("add_item"):
            # FIX: removed the extra space in " Water Bottle"
            item_name = st.selectbox("Item Name", ["Sweater", "Lunchbox", "Water Bottle", "Pencil Case", "Shirt", "Headphones", "Other"])
 
            category = st.selectbox("Category", ["Clothing", "Electronics", "School Supplies", "Food and Drink", "Personal Items", "Other"])
            brand = st.text_input("Brand")
            color = st.selectbox("Color", ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Brown", "Black", "White", "Gray"])
 
            location_found = st.selectbox("Location", ["Cafeteria", "Central Plaza", "Buses", "Gym", "High School Building", "Middle School Building", "Elementary Building", "Preschool Building"])
            date_found = st.date_input("Date found")
            image = st.file_uploader("Image")
 
            submitted = st.form_submit_button("Add Item")
 
        if submitted:
            new_item = Item(item_name, category, brand, color, location_found, date_found, image)
            # save the picture in SQLite
            if image:
                image_data = image.getvalue()
            else:
                image_data = None
 
            cursor.execute("""INSERT INTO lost_items (item_name, category, brand, color, location_found, date_found, image) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (new_item.item_name, new_item.category, new_item.brand, new_item.color, new_item.location_found, str(new_item.date_found), image_data))  # the ? are placeholders
            connect.commit()  # Save
 
            flash("Item added!")
            st.session_state.show_form = False
            st.rerun()  # refresh the webpage.
 
    st.subheader("Uploaded Lost Items")
 
    cursor.execute("SELECT * FROM lost_items")
    lost_items = cursor.fetchall()  # returns a list of tuples
 
    if len(lost_items) == 0:
        st.write("No items are uploaded yet")
 
    else:
        for item in lost_items:
            st.write(f" Id: {item[0]}, Name: {item[1]}, Category: {item[2]}, Brand: {item[3]}, Color: {item[4]}, Location: {item[5]}, Date: {item[6]}")
 
            # Delete an object if necessary
            if st.button("Delete", key=f"delete_item_{item[0]}"):
 
                # Check if there are any existing claim requests
                cursor.execute("SELECT * FROM claims WHERE item_id = ?", (item[0],))
                existing_claim = cursor.fetchone()
 
                if existing_claim:
                    st.warning("This item cannot be deleted because it has claim requests")
 
                else:
                    cursor.execute("DELETE FROM lost_items WHERE id = ?", (item[0],))
                    connect.commit()
                    flash("Item deleted!")
                    st.rerun()
 
    # Shows which database file is being used, useful for checking
    # that admin and student are reading the same file
    st.sidebar.caption(f"Database: {DB_PATH}")
 
 
# ---------------- STUDENT PAGE ----------------
def student_page():
 
    logout_button()
 
    st.header(f"Welcome, {st.session_state.username}")
    show_flash()
 
    # Streamlit does NOT update a page by itself when the admin changes something
    # in another browser. This button re-reads the database.
    if st.button("Refresh"):
        st.rerun()
 
    cursor.execute("SELECT * FROM lost_items")
    lost_items = cursor.fetchall()
 
    # Students' lost items take up more space so, for convenience, I will put their claims at the top
    if "show_my_claims" not in st.session_state:
        st.session_state.show_my_claims = False
 
    if st.button("View My Claims"):
        st.session_state.show_my_claims = not st.session_state.show_my_claims
 
    if st.session_state.show_my_claims:
        st.subheader("My Claim Requests")
        st.caption(f"Showing claims for: {st.session_state.username}")
 
        # Compare usernames ignoring capitals and extra spaces, so "Ana", "ana" and "ana " all match
        cursor.execute("SELECT * FROM claims WHERE LOWER(TRIM(student_username)) = LOWER(TRIM(?))", (st.session_state.username,))
        claims = cursor.fetchall()
 
        # Display the approved or denied claim
        if len(claims) == 0:
            st.write("You have not submitted any claims")
 
        else:
            for claim in claims:
                cursor.execute("SELECT item_name FROM lost_items WHERE id = ?", (claim[0],))
                item = cursor.fetchone()
 
                if item:
                    item_name = item[0]
                else:
                    item_name = "Deleted item"
 
                if claim[3] == "Approved":
                    st.success(f"Your claim for {item_name} has been approved! Please collect it from the Lost and Found at 2:30pm")
                    if st.button("Got it!", key=f"got_it_{claim[0]}"):
                        cursor.execute("UPDATE claims SET status = 'Collected' WHERE item_id = ?", (claim[0],))
                        connect.commit()
                        flash("Item was collected")
                        st.rerun()
                elif claim[3] == "Rejected":
                    st.error(f"Your claim for {item_name} has been rejected. Please contact security for more information")
                elif claim[3] == "Collected":
                    st.success(f"You have collected your {item_name}")
                else:
                    st.info(f"Your request for {item_name} is still pending")
 
        st.divider()
 
    # Add a filter. Make it easier for people to find the lost items
    st.subheader("Search")
    # linear search algorithm
    search_field = st.selectbox("Search by", ["Name", "Category", "Brand", "Color", "Location"])
 
    st.divider()
    st.text("Item names available: Sweater, Lunchbox, Water Bottle, Pencil Case, Shirt, Headphones, Other")
    st.text("Categories available: Clothing, Electronics, School Supplies, Food and Drink, Personal Items, Other")
    st.text("Colors available: Red, Orange, Yellow, Green, Blue, Purple, Brown, Black, White, Gray")
    st.text("Locations available: Cafeteria, Central Plaza, Buses, Gym, High School Building, Middle School Building, Elementary Building, Preschool Building")
    st.divider()
 
    search_text = st.text_input("Enter what you are looking for (e.g. red):").strip()
 
    filtered_items = []
    if search_text == "":
        filtered_items = lost_items
    else:
        for item in lost_items:
            if search_field == "Name":
                value = item[1]
            elif search_field == "Category":
                value = item[2]
            elif search_field == "Brand":
                value = item[3]
            elif search_field == "Color":
                value = item[4]
            else:
                value = item[5]
 
            if value and search_text.lower() in value.lower():
                filtered_items.append(item)
 
    # View the lost items
    # FIX: different message when there are no items vs. when the search found nothing
    if len(lost_items) == 0:
        st.write("No lost items have been uploaded yet.")
    elif len(filtered_items) == 0:
        st.write("No items match your search.")
 
    for item in filtered_items:
        col1, col2 = st.columns(2)
 
        with col1:
            if item[7]:
                st.image(item[7], width=300)
 
        with col2:
            st.write(f"{item[1]}")
            st.write(f"Category: {item[2]}")
            st.write(f"Brand: {item[3]}")
            st.write(f"Color: {item[4]}")
            st.write(f"Location found: {item[5]}")
            st.write(f"Date found: {item[6]}")
 
        # Claim button
        if st.button("Claim", key=f"claim_{item[0]}"):  # the key prevents issues if there are duplicates
 
            cursor.execute("SELECT * FROM claims WHERE item_id = ?", (item[0],))
            existing_claim = cursor.fetchone()  # fetchone retrieves one row
 
            if existing_claim:
                st.warning("This item has already been claimed.")
 
            else:
                cursor.execute("""INSERT INTO claims(item_id, student_username, claim_date, status) VALUES (?, ?, ?, ?)""",
                               (item[0], st.session_state.username, str(date.today()), "Pending"))
                connect.commit()
                flash("Claim submitted!")
                st.rerun()
 
        st.divider()  # Draw a horizontal line across the page, separate the objects
 
 
# ---------------- PAGE ROUTER ----------------
if st.session_state.page == "login":
    home_page()
 
elif st.session_state.page == "admin":
    admin_page()
 
elif st.session_state.page == "student":
    student_page()
