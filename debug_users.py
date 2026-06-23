import streamlit as st
from database import debug_list_all_users, debug_search_user

st.title("Debug: User Lookup")

st.header("All Users in Database")
all_users = debug_list_all_users()
if all_users:
    st.write(f"**Total users: {len(all_users)}**")
    for u in all_users:
        st.write(f"ID: {u['id']} | Username: `{u['username']}`")
else:
    st.warning("No users found")

st.divider()

st.header("Search for User")
search_name = st.text_input("Username to search:", value="ClosedGarden")
if search_name:
    result = debug_search_user(search_name)
    st.json(result)
