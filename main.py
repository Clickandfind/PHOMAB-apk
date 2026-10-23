# PHOMAB Super App Version 6
# Designed for Pydroid 3 + Kivy
# Adds account-aware ride history and persistent local PHOMAB AI chat history.
# Accounts are device-only; this is not yet an online multi-user service.

import sqlite3
import hashlib
import hmac
import os
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


NAVY = (0.07, 0.12, 0.24, 1)
BLUE = (0.10, 0.39, 0.88, 1)
LIGHT = (0.95, 0.97, 1, 1)
WHITE = (1, 1, 1, 1)
DARK = (0.12, 0.15, 0.22, 1)
GREY = (0.40, 0.44, 0.52, 1)
GREEN = (0.10, 0.55, 0.34, 1)
ORANGE = (0.86, 0.42, 0.10, 1)


class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(12)
        self.spacing = dp(8)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*WHITE)
            self.bg = RoundedRectangle(radius=[dp(14)])
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size


class PhomabApp(App):
    def build(self):
        self.title = "PHOMAB Super App"
        self.db_path = self.user_data_dir + "/phomab_data.db"
        self.create_database()
        self.current_ride_id = None
        self.current_user_id = None
        self.current_username = None
        self.root_box = BoxLayout(orientation="vertical", spacing=0)
        with self.root_box.canvas.before:
            Color(*LIGHT)
            self.background = RoundedRectangle()
        self.root_box.bind(pos=self._update_background, size=self._update_background)

        header = BoxLayout(size_hint_y=None, height=dp(76), padding=[dp(16), dp(10)], spacing=dp(8))
        with header.canvas.before:
            Color(*NAVY)
            self.header_bg = RoundedRectangle()
        header.bind(pos=self._update_header, size=self._update_header)

        title_box = BoxLayout(orientation="vertical", spacing=dp(1))
        title_box.add_widget(Label(text="[b]PHOMAB[/b]", markup=True, color=WHITE,
                                   font_size="24sp", halign="left", valign="middle"))
        title_box.add_widget(Label(text="Homes • Services • Jobs • Rides", color=(0.80, 0.86, 1, 1),
                                   font_size="11sp", halign="left", valign="middle"))
        header.add_widget(title_box)
        profile_btn = Button(text="Profile", size_hint_x=None, width=dp(88),
                        background_normal="", background_color=(0.18, 0.28, 0.44, 1), color=WHITE)
        profile_btn.bind(on_release=lambda *_: self.show_page("Profile"))
        header.add_widget(profile_btn)
        ai_btn = Button(text="AI", size_hint_x=None, width=dp(65),
                        background_normal="", background_color=BLUE, color=WHITE)
        ai_btn.bind(on_release=lambda *_: self.show_ai())
        header.add_widget(ai_btn)
        self.root_box.add_widget(header)

        self.content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.root_box.add_widget(self.content)

        nav = GridLayout(cols=5, size_hint_y=None, height=dp(62), spacing=dp(4), padding=[dp(5), dp(6)])
        for text, page in [("Home", "Home"), ("Rides", "Rides"), ("Homes", "Homes"),
                           ("Services", "Services"), ("Jobs", "Jobs")]:
            btn = Button(text=text, font_size="12sp", background_normal="",
                         background_color=BLUE if page == "Home" else NAVY, color=WHITE)
            btn.bind(on_release=lambda instance, p=page: self.show_page(p))
            nav.add_widget(btn)
        self.root_box.add_widget(nav)

        self.show_page("Home")
        return self.root_box

    def _update_background(self, *_):
        self.background.pos = self.root_box.pos
        self.background.size = self.root_box.size

    def _update_header(self, widget, *_):
        self.header_bg.pos = widget.pos
        self.header_bg.size = widget.size

    def label(self, text, size=15, color=DARK, markup=False, height=None):
        lbl = Label(text=text, font_size=f"{size}sp", color=color, markup=markup,
                    size_hint_y=None if height else 1, height=dp(height) if height else 0,
                    halign="left", valign="middle")
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        return lbl

    def button(self, text, callback, color=BLUE, height=46):
        b = Button(text=text, size_hint_y=None, height=dp(height), background_normal="",
                   background_color=color, color=WHITE, font_size="14sp")
        b.bind(on_release=callback)
        return b

    def text_input(self, hint, text="", input_filter=None):
        return TextInput(hint_text=hint, text=text, multiline=False, size_hint_y=None,
                         height=dp(44), padding=[dp(10), dp(10)], font_size="15sp",
                         input_filter=input_filter)

    def add_card(self, parent, title, description=None):
        card = Card()
        card.add_widget(self.label(f"[b]{title}[/b]", 17, NAVY, True, 28))
        if description:
            card.add_widget(self.label(description, 13, GREY, height=42))
        parent.add_widget(card)
        return card

    def show_page(self, page):
        self.content.clear_widgets()
        if page == "Home":
            self.page_home()
        elif page == "Rides":
            self.page_rides()
        elif page == "Homes":
            self.page_listings("Homes")
        elif page == "Services":
            self.page_listings("Services")
        elif page == "Jobs":
            self.page_listings("Jobs")
        elif page == "Profile":
            self.page_profile()

    def make_scroll(self):
        scroll = ScrollView(do_scroll_x=False)
        stack = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        stack.bind(minimum_height=stack.setter("height"))
        scroll.add_widget(stack)
        self.content.add_widget(scroll)
        return stack

    def page_home(self):
        stack = self.make_scroll()
        stack.add_widget(self.label("Welcome", 24, NAVY, height=38))
        stack.add_widget(self.label("One app to move, find a home, get services and discover work.", 14, GREY, height=42))
        card = self.add_card(stack, "Your marketplace", "Choose a section to get started. Your own listings and ride history are saved on this device.")
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(150))
        options = [
            ("🚗  Rides", "Rides"),
            ("🏠  Homes", "Homes"),
            ("🛠  Services", "Services"),
            ("💼  Jobs", "Jobs"),
        ]
        for text, page in options:
            b = Button(text=text, background_normal="", background_color=(0.12, 0.22, 0.40, 1),
                       color=WHITE, font_size="15sp")
            b.bind(on_release=lambda instance, p=page: self.show_page(p))
            grid.add_widget(b)
        card.add_widget(grid)
        card2 = self.add_card(stack, "How rides work",
                              "Passengers offer a fare. Drivers accept or counteroffer. The passenger chooses a driver.")
        card2.add_widget(self.button("Try a ride request", lambda *_: self.show_page("Rides")))
        card3 = self.add_card(stack, "Built for trust")
        card3.add_widget(self.label("• Driver and provider verification planned\n• Ratings and reports planned\n• Cash or supported digital payment\n• Clear prices and agreed fares", 14, DARK, height=95))

    def page_rides(self):
        stack = self.make_scroll()
        stack.add_widget(self.label("Rides", 24, NAVY, height=38))
        stack.add_widget(self.label("Request a ride and negotiate your fare.", 14, GREY, height=28))
        card = self.add_card(stack, "1. Trip details", "Enter pickup and destination for this demo.")
        self.pickup = self.text_input("Pickup location (e.g. home, school)")
        self.destination = self.text_input("Destination")
        self.fare = self.text_input("Your proposed fare (numbers only)", input_filter="int")
        card.add_widget(self.pickup)
        card.add_widget(self.destination)
        card.add_widget(self.fare)
        self.payment = Spinner(text="Cash payment", values=("Cash payment", "Digital payment"),
                               size_hint_y=None, height=dp(44))
        card.add_widget(self.payment)
        self.role = Spinner(text="Passenger", values=("Passenger", "Driver"),
                            size_hint_y=None, height=dp(44))
        card.add_widget(self.role)
        card.add_widget(self.button("Submit ride request", self.submit_ride, GREEN))

        self.ride_result = self.add_card(stack, "2. Driver offers", "Demo offers only — no real drivers are connected.")
        self.ride_result.add_widget(self.label("Submit your trip details to see sample offers.", 13, GREY, height=28))

        driver_card = self.add_card(stack, "Driver demo", "Private car owners and registered taxi drivers may be eligible, subject to local laws and verification.")
        driver_card.add_widget(self.label("Drivers can accept a fare or send a counteroffer. Real onboarding and compliance checks are not active in this prototype.", 13, GREY, height=60))
        driver_card.add_widget(self.button("Make a sample counteroffer", self.counteroffer, ORANGE))
        driver_card.add_widget(self.button("View saved ride history", self.show_ride_history, BLUE))

    def submit_ride(self, *_):
        pickup = self.pickup.text.strip()
        destination = self.destination.text.strip()
        fare = self.fare.text.strip()
        if not pickup or not destination or not fare:
            self.popup("Missing information", "Please enter pickup, destination and a proposed fare.")
            return
        if pickup.lower() == destination.lower():
            self.popup("Check locations", "Pickup and destination should be different.")
            return
        try:
            amount = int(fare)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.popup("Check fare", "Enter a fare greater than zero using numbers only.")
            return
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO rides (pickup, destination, proposed_fare, payment, role, status, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pickup, destination, amount, self.payment.text, self.role.text, "Requested (demo)", datetime.now().isoformat(timespec="seconds"), self.current_user_id)
            )
            self.current_ride_id = cur.lastrowid
        self.ride_result.clear_widgets()
        self.ride_result.add_widget(self.label("[b]Your saved request (demo)[/b]", 15, NAVY, True, 25))
        self.ride_result.add_widget(self.label(f"From: {pickup}\nTo: {destination}\nYour offer: ${amount}\nPayment: {self.payment.text}", 14, DARK, height=85))
        self.ride_result.add_widget(self.label("Available sample driver offers", 14, NAVY, height=26))
        for name, vehicle, offer, eta in [
            ("Tariro M.", "Toyota Aqua • 4.8★", amount, "6 min away"),
            ("Farai K.", "Honda Fit • 4.7★", amount + 2, "9 min away"),
            ("Taxi Partner", "Registered taxi • demo", max(1, amount - 1), "11 min away"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(66), spacing=dp(8))
            info = Label(text=f"[b]{name}[/b]\n{vehicle} • {eta}\nOffer: ${offer}", markup=True,
                         color=DARK, halign="left", valign="middle", font_size="12sp")
            info.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            row.add_widget(info)
            choose = Button(text="Choose", size_hint_x=None, width=dp(78), background_normal="",
                            background_color=GREEN, color=WHITE)
            choose.bind(on_release=lambda instance, n=name, o=offer: self.choose_driver(n, o))
            row.add_widget(choose)
            self.ride_result.add_widget(row)

    def choose_driver(self, name, offer):
        if self.current_ride_id is not None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE rides SET selected_driver=?, agreed_fare=?, status=? WHERE id=?",
                    (name, offer, "Driver selected (demo)", self.current_ride_id)
                )
        self.popup("Demo selection saved", f"You selected {name} at ${offer}.\n\nYour choice is saved in local ride history. No driver has been contacted and no ride has been booked.")

    def show_ride_history(self, *_):
        with sqlite3.connect(self.db_path) as conn:
            rides = conn.execute(
                """SELECT pickup, destination, proposed_fare, payment,
                          selected_driver, agreed_fare, status, created_at
                   FROM rides
                   WHERE user_id IS ?
                   ORDER BY id DESC LIMIT 30""",
                (self.current_user_id,)
            ).fetchall()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        scroll = ScrollView(do_scroll_x=False)
        items = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        items.bind(minimum_height=items.setter("height"))
        if not rides:
            items.add_widget(self.label("No saved rides yet.", 14, GREY, height=40))
        for pickup, destination, fare, payment, driver, agreed, status, created in rides:
            chosen = f"\nDriver: {driver} • Agreed fare: ${agreed}" if driver else "\nNo driver selected"
            items.add_widget(self.label(
                f"{pickup} → {destination}\nOffer: ${fare} • {payment}{chosen}\n{status} • {created}",
                13, DARK, height=78
            ))
        scroll.add_widget(items)
        box.add_widget(scroll)
        box.add_widget(self.button("Close", lambda *_: popup.dismiss(), GREEN))
        popup = Popup(title="Saved ride history", content=box, size_hint=(0.92, 0.8))
        popup.open()

    def counteroffer(self, *_):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        box.add_widget(self.label("Enter a sample driver counteroffer:", 14, DARK, height=28))
        amount = self.text_input("Counteroffer amount", input_filter="int")
        box.add_widget(amount)
        btn = self.button("Send demo counteroffer", lambda *_: self.popup("Counteroffer demo", f"Sample counteroffer: ${amount.text or 'not entered'}\n\nThis does not contact a real passenger."), ORANGE)
        box.add_widget(btn)
        Popup(title="Driver counteroffer", content=box, size_hint=(0.86, None), height=dp(210)).open()

    def page_listings(self, section):
        stack = self.make_scroll()
        stack.add_widget(self.label(section, 24, NAVY, height=38))
        descriptions = {
            "Homes": "Find rental homes and rooms, or advertise a property.",
            "Services": "Find professionals or promote your skills.",
            "Jobs": "Explore work opportunities or post a vacancy.",
        }
        stack.add_widget(self.label(descriptions[section], 14, GREY, height=38))
        search_card = self.add_card(stack, "Search listings")
        search = self.text_input(f"Search {section.lower()} (keyword or area)")
        search_card.add_widget(search)
        search_card.add_widget(self.button("Search", lambda *_: self.search_listings(section, search.text, stack)))
        self.search_listings(section, "", stack, initial=True)
        post_card = self.add_card(stack, f"Post a {section[:-1].lower() if section.endswith('s') else section.lower()}",
                                  "Saved on this device only. It will not be published online.")
        post_title = self.text_input("Title")
        post_details = TextInput(hint_text="Details, area and price (if applicable)", multiline=True,
                                 size_hint_y=None, height=dp(75), font_size="14sp")
        post_card.add_widget(post_title)
        post_card.add_widget(post_details)
        post_card.add_widget(self.button(
            "Save listing on this device",
            lambda *_: self.save_listing(section, post_title.text, post_details.text), GREEN
        ))

    def save_listing(self, section, title, details):
        title = title.strip()
        details = details.strip()
        if not title or not details:
            self.popup("Missing information", "Enter both a title and details before saving.")
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO listings (section, title, details, is_sample, created_at, owner_id) VALUES (?, ?, ?, 0, ?, ?)",
                (section, title, details, datetime.now().isoformat(timespec="seconds"), self.current_user_id)
            )
        self.popup("Listing saved", "Your listing has been saved on this device. It is not visible to other users yet.")
        self.show_page(section)

    def search_listings(self, section, query, stack, initial=False):
        for child in list(stack.children):
            if getattr(child, "is_listing_results", False):
                stack.remove_widget(child)
        results = Card()
        results.is_listing_results = True
        results.add_widget(self.label("[b]Listings[/b]", 16, NAVY, True, 26))
        q = "%" + query.strip().lower() + "%"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, title, details, is_sample, owner_id FROM listings WHERE section=? AND (lower(title) LIKE ? OR lower(details) LIKE ?) ORDER BY is_sample DESC, id DESC",
                (section, q, q)
            ).fetchall()
        if not rows:
            results.add_widget(self.label("No matching listings yet. Try another search or add a listing below.", 13, GREY, height=48))
        for listing_id, title, details, is_sample, owner_id in rows:
            row = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None,
                            height=dp(112 if not is_sample else 92))
            row.add_widget(self.label(f"[b]{title}[/b]", 14, DARK, True, 24))
            row.add_widget(self.label(details, 12, GREY, height=38))
            if is_sample:
                row.add_widget(self.button("View sample details", lambda *_ , t=title, d=details: self.popup(t, d + "\n\nSample listing only. No real contact is available."), BLUE, 34))
            elif owner_id == self.current_user_id:
                row.add_widget(self.button("Delete my listing", lambda *_ , lid=listing_id, sec=section: self.delete_listing(lid, sec), ORANGE, 34))
            else:
                row.add_widget(self.label("Posted by a local user", 11, GREY, height=22))
            results.add_widget(row)
        stack.add_widget(results)

    def delete_listing(self, listing_id, section):
        with sqlite3.connect(self.db_path) as conn:
            if self.current_user_id is None:
                conn.execute("DELETE FROM listings WHERE id=? AND is_sample=0 AND owner_id IS NULL", (listing_id,))
            else:
                conn.execute("DELETE FROM listings WHERE id=? AND is_sample=0 AND owner_id=?", (listing_id, self.current_user_id))
        self.popup("Listing removed", "Your local listing has been removed.")
        self.show_page(section)

    def create_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL,
                is_sample INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                owner_id INTEGER
            )""")
            # Upgrade existing Version 4 databases safely.
            listing_columns = [row[1] for row in conn.execute("PRAGMA table_info(listings)").fetchall()]
            if "owner_id" not in listing_columns:
                conn.execute("ALTER TABLE listings ADD COLUMN owner_id INTEGER")
            conn.execute("""CREATE TABLE IF NOT EXISTS rides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pickup TEXT NOT NULL,
                destination TEXT NOT NULL,
                proposed_fare INTEGER NOT NULL,
                payment TEXT NOT NULL,
                role TEXT NOT NULL,
                selected_driver TEXT,
                agreed_fare INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                user_id INTEGER
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            ride_columns = [row[1] for row in conn.execute("PRAGMA table_info(rides)").fetchall()]
            if "user_id" not in ride_columns:
                conn.execute("ALTER TABLE rides ADD COLUMN user_id INTEGER")
            count = conn.execute("SELECT COUNT(*) FROM listings WHERE is_sample=1").fetchone()[0]
            if count == 0:
                samples = {
                    "Homes": [
                        ("Room to rent", "Sample • residential area"),
                        ("Two-bedroom house", "Sample • family home"),
                        ("Bachelor flat", "Sample • near shops"),
                    ],
                    "Services": [
                        ("Electrician", "Sample provider • repairs"),
                        ("Plumber", "Sample provider • leaks and fittings"),
                        ("Maths tutor", "Sample provider • lessons"),
                    ],
                    "Jobs": [
                        ("Shop assistant", "Sample vacancy • full-time"),
                        ("Junior computer technician", "Sample vacancy • entry-level"),
                        ("Part-time tutor", "Sample vacancy • flexible"),
                    ],
                }
                now = datetime.now().isoformat(timespec="seconds")
                for section, entries in samples.items():
                    for title, details in entries:
                        conn.execute(
                            "INSERT INTO listings (section, title, details, is_sample, created_at) VALUES (?, ?, ?, 1, ?)",
                            (section, title, details, now)
                        )

    def page_profile(self):
        stack = self.make_scroll()
        stack.add_widget(self.label("Profile & account", 24, NAVY, height=38))
        if self.current_user_id is None:
            card = self.add_card(stack, "Browsing as guest", "Create a local account to label your listings and keep them separate from other profiles on this device.")
            card.add_widget(self.button("Create account", lambda *_: self.account_form("register"), GREEN))
            card.add_widget(self.button("Log in", lambda *_: self.account_form("login"), BLUE))
            card.add_widget(self.button("Continue browsing as guest", lambda *_: self.show_page("Home"), NAVY))
        else:
            card = self.add_card(stack, f"Welcome, {self.current_username}", "This account is stored on this device only. It is not an online account yet.")
            with sqlite3.connect(self.db_path) as conn:
                listings = conn.execute("SELECT COUNT(*) FROM listings WHERE is_sample=0 AND owner_id=?", (self.current_user_id,)).fetchone()[0]
                rides = conn.execute("SELECT COUNT(*) FROM rides WHERE user_id=?", (self.current_user_id,)).fetchone()[0]
            card.add_widget(self.label(f"Your listings: {listings}\nYour saved rides: {rides}", 14, DARK, height=48))
            card.add_widget(self.button("Log out", self.logout, ORANGE))
        stack.add_widget(self.label("Security note: passwords are stored as salted PBKDF2 hashes, not plain text. For a public launch, accounts must move to a secure online backend.", 12, GREY, height=70))

    def account_form(self, mode):
        is_register = mode == "register"
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(9))
        box.add_widget(self.label("Create a local account" if is_register else "Log in", 19, NAVY, height=32))
        username = self.text_input("Username")
        email = self.text_input("Email address") if is_register else None
        password = self.text_input("Password")
        password.password = True
        box.add_widget(username)
        if email:
            box.add_widget(email)
        box.add_widget(password)
        def submit(*_):
            name = username.text.strip()
            mail = email.text.strip().lower() if email else ""
            secret = password.text
            if not name or not secret or (is_register and not mail):
                self.popup("Missing information", "Please fill in every field.")
                return
            if len(secret) < 8:
                self.popup("Password too short", "Use at least 8 characters for your password.")
                return
            try:
                with sqlite3.connect(self.db_path) as conn:
                    if is_register:
                        salt = os.urandom(16).hex()
                        digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), bytes.fromhex(salt), 180000).hex()
                        conn.execute("INSERT INTO users (username, email, salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                                     (name, mail, salt, digest, datetime.now().isoformat(timespec="seconds")))
                        user = conn.execute("SELECT id, username FROM users WHERE username=? COLLATE NOCASE", (name,)).fetchone()
                    else:
                        user = conn.execute("SELECT id, username, salt, password_hash FROM users WHERE username=? COLLATE NOCASE", (name,)).fetchone()
                        if user:
                            digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), bytes.fromhex(user[2]), 180000).hex()
                            if not hmac.compare_digest(digest, user[3]):
                                user = None
                            else:
                                user = (user[0], user[1])
                if not user:
                    self.popup("Login failed", "Username or password is incorrect.")
                    return
                self.current_user_id, self.current_username = user
                popup.dismiss()
                self.popup("Account ready", f"You are signed in as {self.current_username}. This account exists on this device only.")
                self.show_page("Profile")
            except sqlite3.IntegrityError:
                self.popup("Account already exists", "That username or email is already registered on this device. Try logging in or use another one.")
            except Exception as exc:
                self.popup("Account error", f"Could not complete this action: {exc}")
        box.add_widget(self.button("Create account" if is_register else "Log in", submit, GREEN))
        box.add_widget(self.button("Cancel", lambda *_: popup.dismiss(), NAVY))
        popup = Popup(title="PHOMAB Account", content=box, size_hint=(0.92, None), height=dp(390 if is_register else 320))
        popup.open()

    def logout(self, *_):
        self.current_user_id = None
        self.current_username = None
        self.popup("Logged out", "You are now browsing as a guest. Your saved local data remains on this device.")
        self.show_page("Home")

    def show_ai(self):
        popup_box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        popup_box.add_widget(self.label("PHOMAB AI", 20, NAVY, height=32))
        popup_box.add_widget(self.label(
            "Your local chat assistant for Rides, Homes, Services and Jobs. "
            "Chat history is saved on this device. This version is not yet connected "
            "to an online AI model.", 12, GREY, height=48
        ))

        scroll = ScrollView(do_scroll_x=False, size_hint_y=1)
        messages_box = BoxLayout(
            orientation="vertical", spacing=dp(8), size_hint_y=None,
            padding=[dp(4), dp(4)]
        )
        messages_box.bind(minimum_height=messages_box.setter("height"))
        scroll.add_widget(messages_box)
        popup_box.add_widget(scroll)

        def add_message(role, message, created_at=None):
            prefix = "You" if role == "user" else "PHOMAB AI"
            color = BLUE if role == "user" else DARK
            item = Label(
                text=f"[b]{prefix}[/b]  {message}", markup=True, color=color,
                halign="left", valign="top", size_hint_y=None,
                height=dp(66), font_size="13sp"
            )
            item.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
            item.bind(texture_size=lambda inst, val: setattr(inst, "height", max(dp(42), val[1] + dp(12))))
            messages_box.add_widget(item)

        with sqlite3.connect(self.db_path) as conn:
            history = conn.execute(
                "SELECT role, message, created_at FROM ai_messages WHERE user_id IS ? ORDER BY id DESC LIMIT 40",
                (self.current_user_id,)
            ).fetchall()
        for role, message, created_at in reversed(history):
            add_message(role, message, created_at)

        if not history:
            add_message("assistant", "Hello! I can guide you around PHOMAB. Ask me about rides, rentals, services or jobs.")

        question = TextInput(
            hint_text="Type your message here...", multiline=True,
            size_hint_y=None, height=dp(72), font_size="14sp",
            padding=[dp(10), dp(10)]
        )
        popup_box.add_widget(question)

        def create_answer(raw_question):
            q = raw_question.lower()
            if any(word in q for word in ("ride", "driver", "fare", "pickup", "destination", "taxi")):
                return ("Open Rides, enter your pickup and destination, propose a fare, "
                        "then compare the sample driver offers. The offers are demonstrations; "
                        "no real driver is contacted.")
            if any(word in q for word in ("house", "rent", "room", "landlord", "property", "home")):
                return ("Open Homes and search by property type or area. You can save a local listing. "
                        "Before paying a deposit, inspect the property and independently verify the landlord.")
            if any(word in q for word in ("plumb", "electric", "service", "repair", "provider", "tutor")):
                return ("Open Services to search for a provider or save a service listing. "
                        "Confirm prices, references and qualifications where required before agreeing to work.")
            if any(word in q for word in ("job", "work", "vacancy", "employ", "career", "cv", "resume")):
                return ("Open Jobs to search vacancies or save a listing. Check the employer carefully "
                        "and do not pay a fee for a guaranteed job.")
            if any(word in q for word in ("account", "login", "password", "profile")):
                return ("Open Profile to create a local account or log in. Accounts currently exist "
                        "only on this device and are not synced online.")
            if any(word in q for word in ("hello", "hi", "hey", "good morning", "good afternoon")):
                return ("Hello! I'm the PHOMAB demo assistant. I can help you navigate Rides, Homes, "
                        "Services and Jobs.")
            return ("I can currently give guidance about PHOMAB Rides, Homes, Services, Jobs and Profiles. "
                    "This is a local demo assistant, not a full online AI model yet.")

        def send_message(*_):
            message = question.text.strip()
            if not message:
                self.popup("Empty message", "Type a message before sending.")
                return
            now = datetime.now().isoformat(timespec="seconds")
            answer_text = create_answer(message)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO ai_messages (user_id, role, message, created_at) VALUES (?, 'user', ?, ?)",
                    (self.current_user_id, message, now)
                )
                conn.execute(
                    "INSERT INTO ai_messages (user_id, role, message, created_at) VALUES (?, 'assistant', ?, ?)",
                    (self.current_user_id, answer_text, datetime.now().isoformat(timespec="seconds"))
                )
            add_message("user", message)
            add_message("assistant", answer_text)
            question.text = ""
            scroll.scroll_y = 0

        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        actions.add_widget(self.button("Send", send_message, GREEN))
        def clear_chat(*_):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM ai_messages WHERE user_id IS ?", (self.current_user_id,))
            messages_box.clear_widgets()
            add_message("assistant", "Chat cleared. How can I help you with PHOMAB?")
            self.popup("Chat cleared", "The local chat history for this profile has been cleared.")
        actions.add_widget(self.button("Clear chat", clear_chat, ORANGE))
        actions.add_widget(self.button("Close", lambda *_: popup.dismiss(), NAVY))
        popup_box.add_widget(actions)

        popup = Popup(title="PHOMAB AI", content=popup_box, size_hint=(0.96, 0.92))
        popup.open()

    def popup(self, title, message):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        lbl = Label(text=message, color=DARK, halign="left", valign="middle")
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        box.add_widget(lbl)
        box.add_widget(self.button("OK", lambda *_: popup.dismiss(), GREEN))
        popup = Popup(title=title, content=box, size_hint=(0.88, None), height=dp(250))
        popup.open()


if __name__ == "__main__":
    PhomabApp().run()
