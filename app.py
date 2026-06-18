import streamlit as st
import pandas as pd
import os

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import cv2
from pyzbar.pyzbar import decode

class QRScanner(VideoProcessorBase):
    def __init__(self):
        self.last_qr = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded = decode(img)

        for d in decoded:
            x, y, w, h = d.rect
            qr_data = d.data.decode("utf-8")

            self.last_qr = qr_data

            cv2.rectangle(img, (x,y), (x+w, y+h), (0,255,0), 2)
            cv2.putText(img, qr_data, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0,255,0), 2)

        return img


CAPACITY = {

    # 서울 → 다빈치
    "월~목 | 서울→다빈치 | 07:50 A": 40,
    "월~목 | 서울→다빈치 | 07:55 A": 40,
    "월~목 | 서울→다빈치 | 07:55 B": 40,
    "월~목 | 서울→다빈치 | 08:50 A": 40,

    "금 | 서울→다빈치 | 07:50 A": 40,
    "금 | 서울→다빈치 | 07:55 A": 40,
    "금 | 서울→다빈치 | 08:50 A": 40,

    # 다빈치 → 서울
    "월~목 | 다빈치→서울 | 14:40 A": 40,
    "월~목 | 다빈치→서울 | 15:40 A": 40,
    "월~목 | 다빈치→서울 | 17:40 A": 40,
    "월~목 | 다빈치→서울 | 18:40 A": 40,

    "금 | 다빈치→서울 | 14:40 A": 40,
    "금 | 다빈치→서울 | 17:40 A": 40,
    "금 | 다빈치→서울 | 18:40 A": 40,
}

CSV_FILE = "tickets.csv"

if not os.path.exists(CSV_FILE):
    pd.DataFrame(
        columns=["student_id", "bus_time", "queue_no", "status"]
    ).to_csv(CSV_FILE, index=False)

st.set_page_config(
    page_title="CAU Smart Shuttle",
    page_icon="🚌",
    layout="centered"
)

# 중앙대 스타일
st.markdown("""
<style>
.stApp {
    background-color:#f5f7fa;
    padding: 10px;
}

/* 전체 폰트 크기 증가 */
html, body, [class*="css"] {
    font-size: 18px;
}

/* 제목 */
h1 {
    color:#005BAC;
    text-align:center;
    font-size:28px;
}

/* 버튼 (모바일 핵심) */
.stButton > button {
    background-color:#005BAC;
    color:white;
    border-radius:12px;
    width:100%;
    height:60px;
    font-size:18px;
}

/* 입력창 */
.stTextInput input {
    height:50px;
    font-size:18px;
}

/* selectbox */
.stSelectbox div {
    font-size:18px;
}

/* 카드 느낌 */
.block-container {
    padding: 1rem 1rem 3rem 1rem;
}

/* 하단 고정 버튼 느낌 */
.fixed-bottom {
    position: fixed;
    bottom: 10px;
    left: 0;
    right: 0;
    padding: 0 10px;
}
</style>
""", unsafe_allow_html=True)


st.title("🚌 CAU Smart Shuttle")
st.caption("중앙대학교 셔틀버스 스마트 체크인 시스템")

if "ticket" not in st.session_state:
    st.session_state.ticket = None

menu = st.sidebar.selectbox(
    "메뉴 선택",
    [
        "학생",
        "내 탑승권",
        "관리자"
    ]
)

# --------------------
# 학생 모드
# --------------------

if menu == "학생":

    st.header("학생 탑승권 발급")

    student_id = st.text_input("학번")

    day = st.selectbox(
        "요일 선택",
        ["월~목", "금"]
    )

    direction = st.selectbox(
        "노선 선택",
        [
            "서울→다빈치",
            "다빈치→서울"
        ]
    )

    available_buses = [
        bus
        for bus in CAPACITY.keys()
        if bus.startswith(day)
        and direction in bus
    ]

    bus_time = st.selectbox(
        "셔틀 선택",
        available_buses
    )

    df = pd.read_csv(CSV_FILE)

    current_count = len(
        df[df["bus_time"] == bus_time]
    )
    
    remaining = CAPACITY[bus_time] - current_count

    st.progress(current_count / CAPACITY[bus_time])

    st.info(f"""
    현재 신청 인원

    {current_count}/{CAPACITY[bus_time]}

    잔여 좌석

    {remaining}
    """)
    
    st.subheader("QR 코드 스캔")

    st.caption(
        "정류장에 부착된 QR 코드를 카메라로 스캔하세요."
    )
    
    ctx = webrtc_streamer(
        key="qr",
        video_processor_factory=QRScanner,
        media_stream_constraints={
            "video": {
                "facingMode": {
                    "ideal": "environment"
                }
            },
            "audio": False,
        }
    )

    qr_code = None

    if ctx.video_processor:
        qr_code = ctx.video_processor.last_qr


    if qr_code:
        st.success(f"인식된 QR: {qr_code}")

    if st.button("탑승권 발급"):

        if student_id == "":
            st.error("학번을 입력하세요.")
            st.stop()

        if not qr_code:
            st.error("QR을 스캔하세요")
            st.stop()
    
        if qr_code != "CAU_SMART_SHUTTLE_STOP":
            st.error("정류장 QR 인증 실패")
            st.stop()
        df = pd.read_csv(CSV_FILE)

        already = df[
            (df["student_id"] == student_id)
            &
            (df["bus_time"] == bus_time)
        ]

        if len(already) > 0:
            st.warning("이미 발급된 탑승권이 있습니다.")
            st.stop()

        current = len(
            df[df["bus_time"] == bus_time]
        )

        if current >= CAPACITY[bus_time]:
            st.error("만석입니다.")
            st.stop()

        queue_no = current + 1

        new_row = pd.DataFrame({
            "student_id":[student_id],
            "bus_time":[bus_time],
            "queue_no":[queue_no],
            "status":["대기"]
        })

        df = pd.concat(
            [df,new_row],
            ignore_index=True
        )

        df.to_csv(CSV_FILE,index=False)

        st.success("탑승권 발급 완료")

        st.session_state.ticket = {
            "student_id": student_id,
            "direction": direction,
            "bus_time": bus_time,
            "queue_no": queue_no,
            "remaining": CAPACITY[bus_time] - queue_no
        }

        st.info("🎫 내 탑승권 메뉴에서 탑승권을 확인하세요.")

        st.rerun()

    st.divider()

    st.subheader("내 예약 조회")

    search_id = st.text_input(
        "예약 조회용 학번"
    )

    if st.button("조회"):

        df = pd.read_csv(CSV_FILE)

        result = df[
            df["student_id"] == search_id
        ]

        if len(result)==0:
            st.warning("예약 내역 없음")

        else:
            st.dataframe(result)

# --------------------
# 내 탑승권
# --------------------

elif menu == "내 탑승권":

    st.header("🎫 내 탑승권")

    ticket = st.session_state.ticket

    if ticket is None:

        st.warning("발급된 탑승권이 없습니다.")

    else:

        st.markdown(f"""
        <div style="
        background:white;
        padding:30px;
        border-radius:20px;
        border:3px solid #005BAC;
        box-shadow:0px 4px 15px rgba(0,0,0,0.15);
        ">

        <h2 style="text-align:center;color:#005BAC;">
        🚌 CAU SMART SHUTTLE
        </h2>

        <h3 style="text-align:center;color:green;">
        탑승 가능
        </h3>

        <p style="
        text-align:center;
        font-size:14px;
        color:gray;
        ">
        기사님께 본 화면을 제시해주세요.
        </p>

        <hr>

        <p><b>학번</b><br>
        {ticket["student_id"]}
        </p>

        <p><b>노선</b><br>
        {ticket["direction"]}
        </p>

        <p><b>버스</b><br>
        {ticket["bus_time"]}
        </p>

        <p><b>대기번호</b></p>

        <p style="
        text-align:center;
        font-size:70px;
        font-weight:bold;
        color:#005BAC;
        margin:10px;
        ">
        {ticket["queue_no"]}
        </p>

        <p><b>잔여좌석</b><br>
        {ticket["remaining"]}
        </p>

        <p><b>상태</b><br>
        대기중
        </p>

        </div>
        """, unsafe_allow_html=True)
        
# --------------------
# 관리자 모드
# --------------------

else:

    st.header("관리자 페이지")

    password = st.text_input(
        "비밀번호",
        type="password"
    )

    if password == "admin123":

        df = pd.read_csv(CSV_FILE)

        st.subheader("전체 예약 현황")

        st.dataframe(df)

        st.divider()

        bus_select = st.selectbox(
            "셔틀 선택",
            list(CAPACITY.keys())
        )

        bus_df = df[
            df["bus_time"] == bus_select
        ]
        
        completed = len(
            bus_df[bus_df["status"] == "탑승완료"]
        )

        waiting = len(
            bus_df[bus_df["status"] == "대기"]
        )

        st.info(f"""
        현재 인원 : {len(bus_df)} / {CAPACITY[bus_select]}

        탑승 완료 : {completed}

        대기 중 : {waiting}
        """)

        st.divider()

        ticket_no = st.number_input(
            "탑승 처리할 번호",
            min_value=1,
            step=1
        )

        if st.button("탑승 완료"):

            idx = df[
                (df["bus_time"] == bus_select)
                &
                (df["queue_no"] == ticket_no)
            ].index

            if len(idx)==0:

                st.error("번호 없음")

            else:

                df.loc[idx,"status"] = "탑승완료"

                df.to_csv(
                    CSV_FILE,
                    index=False
                )

                st.success(
                    f"{ticket_no}번 탑승 처리 완료"
                )
                st.rerun()

    elif password != "":
        st.error("비밀번호 오류")
