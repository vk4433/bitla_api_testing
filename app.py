import requests
import json
import streamlit as st

BASE_URL = "https://gds-qa1.ticketsimply.co.in/gds/api"

st.set_page_config(page_title="Bus Booking API Tester", layout="wide")
st.title("Bus Booking API Tester")

# ── Inputs ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
api_key     = c1.text_input("API Key",      value="TSCQOFAPI14273703")
schedule_id = c2.text_input("Schedule ID",  value="2026062021546")
travel_date = c3.date_input("Travel Date",  value=None)
num_seats   = c4.number_input("Number of Seats", min_value=1, max_value=10, value=1, step=1)
gst_id      = c5.text_input("GST ID",       value="", placeholder="Optional")

run = st.button("Run Booking", use_container_width=True, type="primary")

if run:
    if not api_key or not schedule_id or not travel_date:
        st.error("API Key, Schedule ID and Travel Date are required.")
        st.stop()

    travel_date_str = travel_date.strftime("%Y-%m-%d")

    # ── Run all 3 API calls ───────────────────────────────────────────────────
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

        available_entries = [e for e in raw["bus_layout"]["available"].split(",") if e]
        selected_entries  = available_entries[:num_seats]
        seats_list = [e.split("|")[0] for e in selected_entries]
        fares_list = [e.split("|")[1] for e in selected_entries]

        seat_details = [
            {
                "seat_number":    seats_list[i],
                "fare":           fares_list[i],
                "title":          "Mrs",
                "name":           "Greeshma",
                "age":            "23",
                "sex":            "F",
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

    # ── Operator PNR ──────────────────────────────────────────────────────────
    op_pnr = conf_json.get("result", {}).get("ticket_details", {}).get("operator_pnr")
    if op_pnr:
        st.success(f"Operator PNR: **{op_pnr}**")
    else:
        st.warning("Operator PNR not found in confirm response.")

    st.divider()

    # ── 3 JSONs side by side ──────────────────────────────────────────────────
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
