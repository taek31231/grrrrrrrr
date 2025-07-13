import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import time
import math

# --- 상수 및 초기 설정 ---
# 아인슈타인 반지름을 단위로 가정 (시뮬레이션의 단순화를 위함)
# 실제 값은 렌즈 질량, 거리 등에 따라 수 AU ~ 수십 AU가 될 수 있음
RE = 1.0 

# --- 미세중력렌즈 확대율 함수 (단일 렌즈 모델) ---
def calculate_magnification(u):
    """
    단일 렌즈 미세중력렌즈 효과의 확대율을 계산합니다.
    u: 배경 별과 렌즈 별 사이의 거리 (아인슈타인 반지름으로 정규화된 값)
    
    주의: u가 0에 매우 가까워지면 무한대로 발산할 수 있으므로,
          실제 계산에서는 u의 하한값을 두는 것이 좋습니다.
    """
    # u가 너무 작아지는 경우 (나누기 0 방지 및 물리적 현실성 반영)
    if u < 0.01: # 매우 작은 충격 매개변수
        u = 0.01
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))

# --- Streamlit 앱 시작 ---
st.set_page_config(layout="wide", page_title="미세중력렌즈 시뮬레이터")

st.title("🔭 미세중력렌즈 시각화 및 시뮬레이터")

st.markdown("""
이 앱은 **미세중력렌즈(Microlensing)** 현상을 시각적으로 탐색하고 이해할 수 있도록 돕습니다.
우리와 배경 별 사이에 있는 **렌즈 별**의 중력에 의해 먼 **배경 별**의 빛이 휘어져
밝기가 일시적으로 증가하는 현상을 시뮬레이션합니다.
""")

st.header("✨ 시뮬레이션 제어")

# 세션 상태 초기화
if 'sim_running' not in st.session_state:
    st.session_state.sim_running = False
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0.0
if 'time_history' not in st.session_state:
    st.session_state.time_history = []
if 'magnification_history' not in st.session_state:
    st.session_state.magnification_history = []
if 'event_center_time' not in st.session_state:
    st.session_state.event_center_time = 100 # 시뮬레이션 시작 후 렌즈 별이 중앙에 오는 시간

# 시뮬레이션 버튼
col_buttons = st.columns(3)
with col_buttons[0]:
    if st.button("▶️ 시뮬레이션 시작/계속"):
        st.session_state.sim_running = True
with col_buttons[1]:
    if st.button("⏸️ 일시 정지"):
        st.session_state.sim_running = False
with col_buttons[2]:
    if st.button("🔄 다시 시작"):
        st.session_state.sim_running = False
        st.session_state.current_time = 0.0
        st.session_state.time_history = []
        st.session_state.magnification_history = []
        st.experimental_rerun() # 앱을 처음부터 다시 로드하여 초기 상태로 만듦

st.sidebar.header("⚙️ 시뮬레이션 설정")

event_duration_scale = st.sidebar.slider(
    "이벤트 지속 시간 (상대 단위)",
    min_value=50,
    max_value=300,
    value=200,
    step=10,
    help="렌즈 별이 배경 별 앞을 지나가는 전체 시뮬레이션 시간을 조절합니다. 값이 클수록 천천히 진행됩니다."
)
lens_speed_scale = 5.0 / event_duration_scale # 렌즈 별의 상대 속도 (범위를 약 10 RE 정도로 잡고 시간으로 나눔)

planet_distance = st.sidebar.slider(
    "행성-렌즈 별 거리 (아인슈타인 반지름 대비)",
    min_value=0.1,
    max_value=2.0,
    value=0.5,
    step=0.1,
    help="렌즈 별로부터 행성의 거리를 조절합니다. 아인슈타인 반지름(RE)에 비례합니다."
)
planet_orbit_speed_rad_per_unit_time = st.sidebar.slider(
    "행성 공전 속도 (초당 라디안)",
    min_value=0.05,
    max_value=0.5,
    value=0.1,
    step=0.01,
    help="행성이 렌즈 별 주위를 공전하는 속도를 조절합니다."
)

animation_update_interval = st.sidebar.slider(
    "애니메이션 업데이트 간격 (초)",
    min_value=0.01,
    max_value=0.2,
    value=0.05,
    step=0.01,
    help="각 프레임이 업데이트되는 시간 간격입니다. 값이 작을수록 애니메이션이 빠르고 부드럽습니다."
)

# --- 시뮬레이션 및 광도 곡선 영역 ---
st.header("🌌 시뮬레이션 진행")

# Matplotlib 그래프를 위한 컨테이너 (애니메이션 업데이트용)
plot_container = st.empty()

# 최대 광도 곡선 데이터 포인트 수
max_history_points = 200 # 그래프에 표시할 최대 데이터 포인트 수

# 시뮬레이션 루프
if st.session_state.sim_running:
    # 렌즈 별의 X 위치 (시간에 따라 자동 이동)
    # 렌즈 별이 배경 별 앞을 통과하는 시뮬레이션
    # -5 RE 에서 5 RE 까지 이동한다고 가정
    lens_x = -5.0 + (st.session_state.current_time * lens_speed_scale)

    # 배경 별의 위치 (중앙 고정)
    source_x = 0.0
    source_y = 0.0
    
    # 렌즈 별과 배경 별 사이의 거리 (u) 계산
    # u는 렌즈 별의 X 위치 (배경 별 기준)의 절댓값
    u = abs(lens_x - source_x)
    
    current_magnification = calculate_magnification(u)

    # 행성의 공전 위치 계산 (렌즈 별을 중심으로)
    # 공전 궤도면이 시뮬레이션 평면과 일치
    planet_angle = st.session_state.current_time * planet_orbit_speed_rad_per_unit_time
    planet_x_offset = planet_distance * np.cos(planet_angle)
    planet_y_offset = planet_distance * np.sin(planet_angle) # Y축 오프셋을 사용하여 공전 표현

    # 광도 곡선 데이터 업데이트
    st.session_state.time_history.append(st.session_state.current_time)
    st.session_state.magnification_history.append(current_magnification)

    # 데이터 포인트 제한 (그래프가 너무 길어지는 것을 방지)
    if len(st.session_state.time_history) > max_history_points:
        st.session_state.time_history.pop(0)
        st.session_state.magnification_history.pop(0)

    # --- 시각화 (Matplotlib) ---
    with plot_container.container():
        col_viz, col_curve = st.columns([2, 3]) 

        with col_viz:
            st.subheader("별들의 상대적 위치")
            fig_stars, ax_stars = plt.subplots(figsize=(6, 6))
            ax_stars.set_facecolor('black') # 배경을 검은색으로
            
            # 배경 별 (중앙 고정)
            ax_stars.plot(source_x, source_y, 'o', color='gold', markersize=20, label="배경 별")
            ax_stars.text(source_x + 0.2, source_y + 0.2, "배경 별", color='gold', fontsize=10)

            # 렌즈 별
            ax_stars.plot(lens_x, 0, 'o', color='skyblue', markersize=15, label="렌즈 별")
            ax_stars.text(lens_x + 0.2, 0 + 0.2, "렌즈 별", color='skyblue', fontsize=10)

            # 행성 (렌즈 별 주위 공전)
            # 행성의 위치는 렌즈 별의 위치 + 행성 공전 오프셋
            planet_display_x = lens_x + planet_x_offset
            planet_display_y = planet_y_offset 
            ax_stars.plot(planet_display_x, planet_display_y, 'o', color='gray', markersize=8, label="행성")
            
            # 아인슈타인 링 (렌즈 별 주위 원) - 시각적 가이드
            einstein_ring = plt.Circle((lens_x, 0), RE, color='white', fill=False, linestyle='--', linewidth=0.8, alpha=0.6)
            ax_stars.add_patch(einstein_ring)
            ax_stars.text(lens_x + RE + 0.1, 0, "$R_E$", color='white', fontsize=10, ha='left', va='center')


            ax_stars.set_xlim(-5, 5)
            ax_stars.set_ylim(-5, 5) # Y축 범위도 확장하여 행성 공전 보임
            ax_stars.set_aspect('equal', adjustable='box')
            ax_stars.axis('off') # 축 숨기기
            st.pyplot(fig_stars)
            plt.close(fig_stars) # Matplotlib 경고 방지

        with col_curve:
            st.subheader("광도 곡선")
            fig_curve, ax_curve = plt.subplots(figsize=(8, 6))
            ax_curve.plot(st.session_state.time_history, st.session_state.magnification_history, color='lime')
            ax_curve.set_xlabel("시간 (상대 단위)")
            ax_curve.set_ylabel("배경 별의 상대 밝기 (확대율)")
            ax_curve.set_title("미세중력렌즈 광도 곡선")
            ax_curve.grid(True, linestyle='--', alpha=0.7)
            
            # Y축 범위 조정: 최소 1배부터 최대 확대율까지 + 여유 공간
            min_mag = 1.0 
            max_mag_in_data = max(st.session_state.magnification_history) if st.session_state.magnification_history else 1.0
            ax_curve.set_ylim(bottom=0.95, top=max(max_mag_in_data * 1.1, 1.5)) # 최소 1.5까지 보이게

            # X축 범위는 동적으로 조절
            ax_curve.set_xlim(left=st.session_state.time_history[0] if st.session_state.time_history else 0, 
                              right=st.session_state.time_history[-1] + event_duration_scale * 0.1 if st.session_state.time_history else event_duration_scale)
            st.pyplot(fig_curve)
            plt.close(fig_curve) 
        
        st.caption(f"현재 렌즈-배경 별 상대 거리 (u): {u:.2f}, 현재 확대율: {current_magnification:.2f}")

    # 다음 프레임 업데이트를 위한 시간 증가
    st.session_state.current_time += animation_update_interval
    time.sleep(animation_update_interval)

    # 렌즈 별이 시뮬레이션 범위를 벗어나면 자동으로 정지 (재시작 유도)
    if lens_x > 5.0:
        st.session_state.sim_running = False
        st.info("시뮬레이션이 완료되었습니다. '다시 시작' 버튼을 눌러 처음부터 다시 볼 수 있습니다.")
    else:
        st.rerun() # Streamlit 앱을 다시 실행하여 UI를 업데이트
