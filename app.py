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


class BookingResult:
    def __init__(self, op_pnr, ticket_number, seat_numbers):
        self.op_pnr = op_pnr
        self.ticket_number = ticket_number
        self.seat_numbers = seat_numbers

    def display(self):
        st.info(
            f"**Last Booking** — "
            f"Operator PNR: `{self.op_pnr}` | "
            f"Ticket: `{self.ticket_number}` | "
            f"Seats: `{', '.join(self.seat_numbers)}`"
        )


st.set_page_config(page_title="Bus Booking API Tester", layout="wide")
st.title("Bus Booking API Tester")

keys = load_keys()

if "edit_key" not in st.session_state:
    st.session_state.edit_key = None

if "booking" not in st.session_state:
    st.session_state.booking = None

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

# ── API Key selector (shared across tabs) ─────────────────────────────────────
if keys:
    sel = st.selectbox("API Key", list(keys.keys()) + ["⌨️ Enter manually"], label_visibility="collapsed")
    api_key = keys[sel] if sel != "⌨️ Enter manually" else \
              st.text_input("Custom key", value="TSCQOFAPI14273703", label_visibility="collapsed")
else:
    api_key = st.text_input("API Key", value="TSCQOFAPI14273703")

tab_book, tab_cancel = st.tabs(["Booking", "Cancellation"])

# ── Booking tab ───────────────────────────────────────────────────────────────
with tab_book:
    c2, c3, c4, c5, c6 = st.columns(5)
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
            gents_seats = {
                s.strip()
                for s in raw["bus_layout"].get("gents_seats", "").split(",")
                if s.strip()
            }

            is_female = gender == "Female"
            all_entries = [e for e in raw["bus_layout"]["available"].split(",") if e]
            available_entries = [
                e for e in all_entries
                if (
                    is_female and (not ladies_seats or e.split("|")[0] in ladies_seats)
                ) or (
                    not is_female and (
                        (gents_seats and e.split("|")[0] in gents_seats)
                        or (not gents_seats and e.split("|")[0] not in ladies_seats)
                    )
                )
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
                    "name":           "Greeshma" if is_female else "vinod",
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
            st.session_state.booking = BookingResult(op_pnr, ticket_number, seats_list)
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

    # Persists across reruns; replaced when a new booking succeeds
    if not run and st.session_state.booking:
        st.session_state.booking.display()

# ── Cancellation tab ──────────────────────────────────────────────────────────
with tab_cancel:
    for _k in ("can_cancel_result", "cancel_booking_result", "cancel_ticket_number", "cancel_seat_numbers"):
        if _k not in st.session_state:
            st.session_state[_k] = None

    # Pre-fill from last booking if available
    last = st.session_state.booking
    if last:
        st.info(
            f"**Last Booking** — Operator PNR: `{last.op_pnr}` | "
            f"Ticket: `{last.ticket_number}` | "
            f"Seats: `{', '.join(last.seat_numbers)}`"
        )

    cc1, cc2 = st.columns(2)
    default_ticket = last.ticket_number if last else ""
    default_seats  = ", ".join(last.seat_numbers) if last else ""
    cancel_ticket    = cc1.text_input("Ticket Number", value=default_ticket, placeholder="e.g. TS260620002645407529FFVC")
    cancel_seats_raw = cc2.text_input("Seat Numbers (comma-separated)", value=default_seats, placeholder="e.g. 16,17")

    if st.button("Check Cancellation"):
        if not cancel_ticket.strip() or not cancel_seats_raw.strip():
            st.error("Ticket Number and Seat Numbers are required.")
        else:
            st.session_state.cancel_ticket_number  = cancel_ticket.strip()
            st.session_state.cancel_seat_numbers   = cancel_seats_raw.strip()
            st.session_state.cancel_booking_result = None
            with st.spinner("Checking..."):
                resp = requests.get(
                    f"{BASE_URL}/can_cancel.json",
                    params={
                        "ticket_number": cancel_ticket.strip(),
                        "seat_numbers":  cancel_seats_raw.strip(),
                        "api_key":       api_key,
                    },
                    timeout=15,
                )
            st.session_state.can_cancel_result = resp.json()

    if st.session_state.cancel_booking_result:
        cancel_result  = st.session_state.cancel_booking_result
        cancel_detail  = cancel_result.get("result", {}).get("cancel_ticket", {})
        if cancel_detail:
            st.success(
                f"Cancelled! Refund: ₹{cancel_detail.get('refund_amount', 'N/A')} | "
                f"Charges: ₹{cancel_detail.get('cancellation_charges', 'N/A')}"
            )
        st.json(cancel_result)

    elif st.session_state.can_cancel_result:
        result = st.session_state.can_cancel_result
        info   = result.get("result", {}).get("is_ticket_cancellable", {})

        if info.get("is_cancellable"):
            m1, m2, m3 = st.columns(3)
            m1.metric("Cancel Charge %",      f"{info['cancel_percent']}%")
            m2.metric("Refund Amount",        f"₹{info['refund_amount']}")
            m3.metric("Cancellation Charges", f"₹{info['cancellation_charges']}")

            with st.expander("can_cancel API Response"):
                st.json(result)

            st.warning("Do you want to proceed with cancellation?")
            yes_col, no_col, _ = st.columns([1, 1, 8])

            if yes_col.button("Yes, Cancel", type="primary"):
                with st.spinner("Cancelling..."):
                    cancel_resp = requests.get(
                        f"{BASE_URL}/cancel_booking.json",
                        params={
                            "ticket_number": st.session_state.cancel_ticket_number,
                            "seat_numbers":  st.session_state.cancel_seat_numbers,
                            "api_key":       api_key,
                        },
                        timeout=15,
                    )
                st.session_state.cancel_booking_result = cancel_resp.json()
                st.session_state.can_cancel_result     = None
                st.rerun()

            if no_col.button("No, Keep"):
                st.session_state.can_cancel_result = None
                st.rerun()
        else:
            st.error("This ticket is not cancellable.")
            with st.expander("can_cancel API Response"):
                st.json(result)
