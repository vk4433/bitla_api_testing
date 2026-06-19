import requests
import json
import os
import streamlit as st

BASE_URL = "https://gds-qa1.ticketsimply.co.in/gds/api"
KEYS_FILE = os.path.join(os.path.dirname(__file__), "api_keys.json")


def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_keys(keys_dict):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys_dict, f, indent=2)


st.set_page_config(page_title="Bus Booking API Tester", layout="wide")
st.title("Bus Booking API Tester")

keys = load_keys()

if "edit_key" not in st.session_state:
    st.session_state.edit_key = None

# ── Change API Key ────────────────────────────────────────────────────────────
with st.expander("🔑 Change API Key", expanded=bool(st.session_state.edit_key)):
    editing = st.session_state.edit_key
    fa, fb = st.columns(2)
    kn = fa.text_input("key_name", value=editing or "")
    kv = fb.text_input("key",      value=keys.get(editing, "") if editing else "")
    c1, c2 = st.columns([1, 9])
    if c1.button("💾 Save", type="primary"):
        if kn.strip() and kv.strip():
            if editing and editing != kn.strip():
                keys.pop(editing, None)
            keys[kn.strip()] = kv.strip()
            save_keys(keys)
            st.session_state.edit_key = None
            st.rerun()
        else:
            st.error("Both fields are required.")
    if editing and c2.button("Cancel"):
        st.session_state.edit_key = None
        st.rerun()

    if keys:
        st.divider()
        for name, val in list(keys.items()):
            r1, r2, r3 = st.columns([7, 1, 1])
            r1.markdown(f"**{name}** — `{val}`")
            if r2.button("Edit", key=f"e_{name}"):
                st.session_state.edit_key = name
                st.rerun()
            if r3.button("🗑️", key=f"d_{name}"):
                keys.pop(name)
                save_keys(keys)
                st.rerun()

# ── Inputs ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

if keys:
    sel = c1.selectbox("API Key", list(keys.keys()) + ["⌨️ Enter manually"])
    api_key = keys[sel] if sel != "⌨️ Enter manually" else \
              c1.text_input("Custom key", value="TSCQOFAPI14273703", label_visibility="collapsed")
else:
    api_key = c1.text_input("API Key", value="TSCQOFAPI14273703")

schedule_id = c2.text_input("Schedule ID",  value="2026062021546")
travel_date = c3.date_input("Travel Date",  value=None)
num_seats   = c4.number_input("Number of Seats", min_value=1, max_value=10, value=1, step=1)
gst_id      = c5.text_input("GST ID",       value="", placeholder="Optional")
gender      = c6.selectbox("Gender", ["Female", "Male"])

run = st.button("Run Booking", use_container_width=True, type="primary")

if run:
    if not api_key or not schedule_id or not travel_date:
        st.error("API Key, Schedule ID and Travel Date are required.")
        st.stop()

    travel_date_str = travel_date.strftime("%Y-%m-%d")

    with st.spinner("Running..."):
        # 1. Schedule
        get_resp = requests.get(
            f"{BASE_URL}/schedule/{schedule_id}.json?api_key={api_key}",
            timeout=15,
        )
        schedule_json = get_resp.json()

        raw = schedule_json.get("result")
        if not raw:
            st.error("No result in schedule response.")
            st.stop()

        origin_id      = str(raw["origin_id"])
        destination_id = str(raw["destination_id"])
        boarding_id    = raw["bus_layout"]["boarding_stages"].split("|")[0]
        dropoff_id     = raw["bus_layout"]["dropoff_stages"].split("|")[0]

        ladies_seats = {
            s.strip()
            for s in raw["bus_layout"].get("ladies_seats", "").split(",")
            if s.strip()
        }

        is_female = gender == "Female"
        all_entries = [e for e in raw["bus_layout"]["available"].split(",") if e]
        available_entries = [
            e for e in all_entries
            if is_female or e.split("|")[0] not in ladies_seats
        ]
        selected_entries = available_entries[:num_seats]
        if len(selected_entries) < num_seats:
            st.error(f"Only {len(selected_entries)} seat(s) available for {gender}.")
            st.stop()

        seats_list = [e.split("|")[0] for e in selected_entries]
        fares_list = [e.split("|")[1] for e in selected_entries]

        seat_details = [
            {
                "seat_number":    seats_list[i],
                "fare":           fares_list[i],
                "title":          "Mrs" if is_female else "Mr",
                "name":           "Greeshma" if is_female else "Ravi",
                "age":            "23",
                "sex":            "F" if is_female else "M",
                "is_primary":     "true" if i == 0 else "false",
                "id_card_number": "111111111",
                "disc_amt":       "0",
                "op_comission":   "",
            }
            for i in range(len(selected_entries))
        ]

        gst_details = {"gst_id": gst_id, "registration_name": "goa"} if gst_id.strip() else {}

        payload = {
            "book_ticket": {
                "seat_details": {"seat_detail": seat_details},
                "contact_detail": {
                    "mobile_number": "9885665243",
                    "emergency_name": "",
                    "email": "greeshma@bitlasoft.com",
                },
            },
            "origin_id":      origin_id,
            "destination_id": destination_id,
            "boarding_at":    boarding_id,
            "drop_off":       dropoff_id,
            "no_of_seats":    str(len(seat_details)),
            "travel_date":    travel_date_str,
            **( {"passenger_gst_details": gst_details} if gst_details else {} ),
        }

        # 2. Tentative booking
        tent_resp = requests.post(
            f"{BASE_URL}/tentative_booking/{schedule_id}.json?api_key={api_key}",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        tent_json = tent_resp.json()

        pnr = tent_json.get("result", {}).get("ticket_details", {}).get("pnr_number")
        if not pnr:
            st.error("No PNR returned from tentative booking.")
            col1, col2 = st.columns(2)
            col1.subheader("1. Schedule")
            col1.json(schedule_json)
            col2.subheader("2. Tentative Booking")
            col2.json(tent_json)
            st.stop()

        # 3. Confirm booking
        conf_resp = requests.post(
            f"{BASE_URL}/confirm_booking/{pnr}.json?is_sms=true&api_key={api_key}",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        conf_json = conf_resp.json()

    op_pnr = conf_json.get("result", {}).get("ticket_details", {}).get("operator_pnr")
    ticket_number = conf_json.get("result", {}).get("ticket_details", {}).get("ticket_number")
    if op_pnr and ticket_number:
        st.success(f"Operator PNR: **{op_pnr}**")
        st.success(f"Ticket Number: **{ticket_number}**")
    else:
        st.warning("Operator PNR or Ticket Number not found in confirm response.")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("1. Schedule")
        st.json(schedule_json)
    with col2:
        st.subheader("2. Tentative Booking")
        st.json(tent_json)
    with col3:
        st.subheader("3. Confirm Booking")
        st.json(conf_json)
