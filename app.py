import streamlit as st
import pandas as pd
import gspread

st.set_page_config(
    page_title="Travel Expense Tracker",
    layout="wide"
)
st.caption("Group Travel Expense Tracker")
# -----------------------------
# GOOGLE SHEET CONFIG
# -----------------------------

SHEET_ID = "PASTE_YOUR_SHEET_ID_HERE"

gc = gspread.service_account(filename=r"D:\TADOBACASH\credentials.json")
spreadsheet = gc.open_by_key("1pJOFCVAY0gTCaRu_xM0AXiGea-6kxz1-EmOYOeFZhv8")

members_ws = spreadsheet.worksheet("Members")
expenses_ws = spreadsheet.worksheet("Expenses")

members_df = pd.DataFrame(members_ws.get_all_records())
expenses_df = pd.DataFrame(expenses_ws.get_all_records())

if expenses_df.empty:
    expenses_df = pd.DataFrame(
        columns=["expense_id", "date", "description", "amount", "paid_by", "participants"]
    )

members = members_df["name"].tolist()

# -----------------------------
# SAVE FUNCTION
# -----------------------------

def save_expenses(df):
    expenses_ws.clear()
    data = [df.columns.values.tolist()] + df.values.tolist()
    expenses_ws.update(data)

# -----------------------------
# APP TITLE
# -----------------------------

st.title("Travel Expense Tracker")

# -----------------------------
# ADD EXPENSE
# -----------------------------

st.header("Add Expense")

date = st.date_input("Date")
description = st.text_input("Description")
amount = st.number_input("Amount", min_value=0.0)
payer = st.selectbox("Paid by", members)
participants = st.multiselect("Participants", members, default=[payer])

if st.button("Add Expense"):

    if len(expenses_df) == 0:
        new_id = 1
    else:
        new_id = int(expenses_df["expense_id"].max()) + 1

    new_row = {
        "expense_id": new_id,
        "date": str(date),
        "description": description,
        "amount": amount,
        "paid_by": payer,
        "participants": ",".join(participants)
    }

    expenses_df = pd.concat([expenses_df, pd.DataFrame([new_row])], ignore_index=True)

    save_expenses(expenses_df)

    st.success("Expense added")
    st.rerun()



# -----------------------------
# EXPENSE TABLE
# -----------------------------

st.header("Expenses")
st.dataframe(expenses_df.astype(str))

# -----------------------------
# EDIT / DELETE EXPENSE
# -----------------------------

st.header("Edit / Delete Expense")

if len(expenses_df) > 0:

    selected_id = st.selectbox(
        "Select expense ID",
        expenses_df["expense_id"]
    )

    row = expenses_df[expenses_df["expense_id"] == selected_id].iloc[0]

    edit_date = st.date_input(
        "Date",
        pd.to_datetime(row["date"]),
        key=f"edit_date_{selected_id}"
    )

    edit_desc = st.text_input(
        "Description",
        row["description"],
        key=f"edit_desc_{selected_id}"
    )

    edit_amount = st.number_input(
        "Amount",
        value=float(row["amount"]),
        key=f"edit_amt_{selected_id}"
    )

    edit_payer = st.selectbox(
        "Paid by",
        members,
        index=members.index(row["paid_by"]),
        key=f"edit_payer_{selected_id}"
    )

    edit_participants = st.multiselect(
        "Participants",
        members,
        default=row["participants"].split(","),
        key=f"edit_part_{selected_id}"
    )

    col1, col2 = st.columns(2)

    if col1.button("Update Expense"):

        expenses_df.loc[
            expenses_df["expense_id"] == selected_id,
            ["date","description","amount","paid_by","participants"]
        ] = [
            str(edit_date),
            edit_desc,
            edit_amount,
            edit_payer,
            ",".join(edit_participants)
        ]

        save_expenses(expenses_df)

        st.success("Expense updated")
        st.rerun()

    if col2.button("Delete Expense"):

        expenses_df = expenses_df[
            expenses_df["expense_id"] != selected_id
        ]

        save_expenses(expenses_df)

        st.warning("Expense deleted")
        st.rerun()

# -----------------------------
# TOTAL + PER HEAD
# -----------------------------

total_expense = expenses_df["amount"].astype(float).sum()
per_head = total_expense / len(members) if len(members) else 0

col1, col2 = st.columns([1,1])

with col1:
    st.metric("Total Expense", f"₹ {round(total_expense,2)}")

with col2:
    st.metric("Per Head Expense", f"₹ {round(per_head,2)}")

# -----------------------------
# MY SHARE
# -----------------------------

st.header("My Share")

person = st.selectbox("Select Person", members)

share_total = 0

for _, row in expenses_df.iterrows():

    people = str(row["participants"]).split(",")

    if person in people:
        share_total += float(row["amount"]) / len(people)

st.metric(f"{person}'s Share", f"₹ {round(share_total,2)}")

# -----------------------------
# BALANCE DASHBOARD
# -----------------------------

st.header("Balance Dashboard")

balance = {m: 0 for m in members}

for _, row in expenses_df.iterrows():

    payer = row["paid_by"]
    amount = float(row["amount"])
    people = str(row["participants"]).split(",")

    share = amount / len(people)

    for p in people:
        balance[p] -= share

    balance[payer] += amount

balance_df = pd.DataFrame(balance.items(), columns=["Member", "Balance"])
balance_df["Balance"] = balance_df["Balance"].round(2)

st.dataframe(balance_df)

# -----------------------------
# SETTLEMENT SUGGESTIONS
# -----------------------------

st.header("Settlement Suggestions")

creditors = []
debtors = []

for person, amt in balance.items():

    if amt > 0:
        creditors.append([person, amt])

    elif amt < 0:
        debtors.append([person, -amt])

settlements = []

i = 0
j = 0

while i < len(debtors) and j < len(creditors):

    debtor, d_amt = debtors[i]
    creditor, c_amt = creditors[j]

    pay = min(d_amt, c_amt)

    settlements.append((debtor, creditor, round(pay, 2)))

    debtors[i][1] -= pay
    creditors[j][1] -= pay

    if debtors[i][1] <= 0.01:
        i += 1

    if creditors[j][1] <= 0.01:
        j += 1

if settlements:
    for s in settlements:
        st.write(f"{s[0]} pays {s[1]} ₹{s[2]}")
else:
    st.write("All settled")

# -----------------------------
# WHATSAPP SUMMARY
# -----------------------------

st.header("WhatsApp Settlement Summary")

trip_name = st.text_input("Trip name", value="Trip")

if st.button("Generate Message"):

    if settlements:

        msg = f"*{trip_name} Settlement*\n\n"

        for s in settlements:
            msg += f"{s[0]} pays {s[1]} ₹{s[2]}\n"

        msg += "\nThanks 🙂"

        st.text_area("Copy message", msg, height=200)

# -----------------------------
# BACKUP
# -----------------------------

st.header("Backup")

csv = expenses_df.to_csv(index=False)

st.download_button(
    label="Download Backup CSV",
    data=csv,
    file_name="travel_expense_backup.csv",
    mime="text/csv"
)