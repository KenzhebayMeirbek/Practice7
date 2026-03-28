import csv
import psycopg2
from connect import get_connection, init_db



def print_table(rows: list[tuple]) -> None:
    if not rows:
        print("  (no contacts found)")
        return
    headers = ("ID", "First name", "Last name", "Phone")
    widths = [max(len(str(h)), max(len(str(r[i])) for r in rows))
              for i, h in enumerate(headers)]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    sep = "  " + "  ".join("-" * w for w in widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v) if v is not None else "" for v in row]))



def insert_from_csv(filepath: str) -> None:
    inserted = skipped = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with get_connection() as conn:
            with conn.cursor() as cur:
                for row in reader:
                    try:
                        cur.execute(
                            """
                            INSERT INTO phonebook (first_name, last_name, phone)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (phone) DO NOTHING;
                            """,
                            (row["first_name"], row.get("last_name"), row["phone"]),
                        )
                        if cur.rowcount:
                            inserted += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        print(f"   Skipping row {row}: {e}")
            conn.commit()
    print(f"[CSV] Inserted {inserted}, skipped {skipped} duplicate(s).")



def insert_from_console() -> None:
    print("\n--- Add new contact ---")
    first_name = input("  First name : ").strip()
    last_name  = input("  Last name  : ").strip() or None
    phone      = input("  Phone      : ").strip()

    if not first_name or not phone:
        print("  [!] First name and phone are required.")
        return

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO phonebook (first_name, last_name, phone)
                    VALUES (%s, %s, %s);
                    """,
                    (first_name, last_name, phone),
                )
            conn.commit()
        print(f"  [+] Contact '{first_name}' added.")
    except psycopg2.errors.UniqueViolation:
        print(f"  [!] Phone '{phone}' already exists.")



def get_all_contacts() -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, first_name, last_name, phone FROM phonebook ORDER BY first_name;"
            )
            return cur.fetchall()


def search_by_name(name: str) -> list[tuple]:
    pattern = f"%{name}%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, phone
                FROM phonebook
                WHERE first_name ILIKE %s OR last_name ILIKE %s
                ORDER BY first_name;
                """,
                (pattern, pattern),
            )
            return cur.fetchall()


def search_by_phone_prefix(prefix: str) -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, phone
                FROM phonebook
                WHERE phone LIKE %s
                ORDER BY phone;
                """,
                (f"{prefix}%",),
            )
            return cur.fetchall()



def update_contact() -> None:
    print("\n--- Update contact ---")
    current_phone = input("  Enter current phone to find contact: ").strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, first_name, last_name, phone FROM phonebook WHERE phone = %s;",
                (current_phone,),
            )
            row = cur.fetchone()

    if not row:
        print(f"  [!] No contact with phone '{current_phone}'.")
        return

    print(f"  Found: ID={row[0]}  {row[1]} {row[2] or ''}  {row[3]}")
    print("  What would you like to update?")
    print("  1 — First name")
    print("  2 — Phone number")
    choice = input("  Choice: ").strip()

    if choice == "1":
        new_first = input("  New first name: ").strip()
        if not new_first:
            print("  [!] Name cannot be empty.")
            return
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE phonebook SET first_name = %s WHERE phone = %s;",
                    (new_first, current_phone),
                )
            conn.commit()
        print(f"  [✓] First name updated to '{new_first}'.")

    elif choice == "2":
        new_phone = input("  New phone number: ").strip()
        if not new_phone:
            print("  [!] Phone cannot be empty.")
            return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE phonebook SET phone = %s WHERE phone = %s;",
                        (new_phone, current_phone),
                    )
                conn.commit()
            print(f"  [✓] Phone updated to '{new_phone}'.")
        except psycopg2.errors.UniqueViolation:
            print(f"  [!] Phone '{new_phone}' is already used by another contact.")
    else:
        print("  [!] Invalid choice.")



def delete_contact() -> None:
    print("\n--- Delete contact ---")
    print("  1 — Delete by first name")
    print("  2 — Delete by phone number")
    choice = input("  Choice: ").strip()

    if choice == "1":
        name = input("  First name: ").strip()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM phonebook WHERE first_name ILIKE %s;", (name,)
                )
                deleted = cur.rowcount
            conn.commit()
        print(f"  Deleted {deleted} contact(s) with first name '{name}'.")

    elif choice == "2":
        phone = input("  Phone: ").strip()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM phonebook WHERE phone = %s;", (phone,)
                )
                deleted = cur.rowcount
            conn.commit()
        print(f"  Deleted {deleted} contact(s) with phone '{phone}'.")

    else:
        print("   Invalid choice.")



MENU = """
       PhoneBook — Practice 7     

 1. Show all contacts             
 2. Search by name                
 3. Search by phone prefix        
 4. Add contact (console)         
 5. Import contacts from CSV      
 6. Update contact                
 7. Delete contact                
 0. Exit                          
"""


def run() -> None:
    init_db()
    while True:
        print(MENU)
        choice = input("  Your choice: ").strip()

        if choice == "1":
            rows = get_all_contacts()
            print(f"\n  Total contacts: {len(rows)}")
            print_table(rows)

        elif choice == "2":
            name = input("  Enter name (or part of name): ").strip()
            rows = search_by_name(name)
            print_table(rows)

        elif choice == "3":
            prefix = input("  Enter phone prefix (e.g. +7700): ").strip()
            rows = search_by_phone_prefix(prefix)
            print_table(rows)

        elif choice == "4":
            insert_from_console()

        elif choice == "5":
            path = input("  CSV file path [contacts.csv]: ").strip() or "contacts.csv"
            insert_from_csv(path)

        elif choice == "6":
            update_contact()

        elif choice == "7":
            delete_contact()

        elif choice == "0":
            print("  Goodbye!")
            break

        else:
            print("  [!] Unknown option, try again.")


if __name__ == "__main__":
    run()
