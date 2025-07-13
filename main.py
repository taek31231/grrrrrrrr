import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os # 파일 저장 및 관리를 위해 추가
import base64 # GIF 파일을 Streamlit에 임베드하기 위해 추가

# --- 상수 및 초기 설정 ---
RE = 1.0 # 아인슈타인 반지름을 단위로 가정

# --- 미세중력렌즈 확대율 함수 (단일 렌즈 모델) ---
def calculate_magnification(u):
    """
    단일 렌즈 미세중력렌즈 효과의 확대율을 계산합니다.
    u: 배경 별과 렌즈 별 사이의 거리 (아인슈타인 반지름으로 정규화된 값)
    """
    if u < 0.01: # u가 너무 작아지는 경우 (무한대 발산 방지 및 물리적 현실성 반영)
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

st.header("✨ 시뮬레이션 제어 및 설정")

# 세션 상태 초기화
if 'animation_created' not in st.session_state:
    st.session_state.animation_created = False
if 'animation_path' not in st.session_state:
    st.session_state.animation_path = None
if 'light_curve_data' not in st.session_state:
    st.session_state.light_curve_data = {'time': [], 'magnification': []}

col_buttons = st.columns(3)
with col_buttons[0]:
    if st.button("▶️ 시뮬레이션 실행 및 애니메이션 생성"):
        st.session_state.animation_created = False # 애니메이션 재생성
        st.session_state.animation_path = None
        st.session_state.light_curve_data = {'time': [], 'magnification': []} # 데이터 초기화
        
        # 시뮬레이션 시작 트리거 (아래에서 실제 애니메이션 생성)
        st.write("애니메이션을 생성 중입니다. 잠시 기다려 주세요...")
        # 이 시점에서 애니메이션 생성 함수를 호출하고 결과를 캐싱
        create_and_display_animation() 
        
with col_buttons[1]:
    if st.button("🔄 시뮬레이션 초기화"):
        st.session_state.animation_created = False
        st.session_state.animation_path = None
        st.session_state.light_curve_data = {'time': [], 'magnification': []}
        st.experimental_rerun() # 앱을 처음부터 다시 로드하여 초기 상태로 만듦

st.sidebar.header("⚙️ 시뮬레이션 설정")

sim_total_frames = st.sidebar.slider(
    "총 시뮬레이션 프레임 수",
    min_value=100,
    max_value=500,
    value=200,
    step=50,
    help="애니메이션의 전체 프레임 수를 조절합니다. 많을수록 부드러워지지만 생성 시간이 길어집니다."
)
sim_duration_units = st.sidebar.slider(
    "렌즈 별 횡단 범위 (상대 거리)",
    min_value=5.0,
    max_value=20.0,
    value=10.0,
    step=1.0,
    help="렌즈 별이 배경 별 앞을 지나가는 총 거리를 조절합니다. (예: 10은 -5RE에서 +5RE까지)"
)
sim_frame_interval_ms = st.sidebar.slider(
    "프레임 간 간격 (ms)",
    min_value=20,
    max_value=200,
    value=50,
    step=10,
    help="애니메이션 프레임 간의 시간 간격입니다. 작을수록 빠릅니다."
)

planet_distance_re = st.sidebar.slider(
    "행성-렌즈 별 거리 (아인슈타인 반지름 대비)",
    min_value=0.1,
    max_value=2.0,
    value=0.5,
    step=0.1,
    help="렌즈 별로부터 행성의 거리를 조절합니다. 아인슈타인 반지름(RE)에 비례합니다."
)
planet_orbit_speed_rad_per_frame = st.sidebar.slider(
    "행성 공전 속도 (프레임당 라디안)",
    min_value=0.01,
    max_value=0.2,
    value=0.05,
    step=0.01,
    help="행성이 렌즈 별 주위를 공전하는 속도입니다. 값이 클수록 빠르게 공전합니다."
)

# --- 애니메이션 생성 및 표시 함수 ---
@st.cache_data(show_spinner="애니메이션을 생성 중입니다... ✨")
def create_and_display_animation():
    fig, (ax_stars, ax_curve) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1, 2]})
    
    # 별 시각화 설정
    ax_stars.set_facecolor('black')
    ax_stars.set_xlim(-sim_duration_units/2 - 1, sim_duration_units/2 + 1)
    ax_stars.set_ylim(-sim_duration_units/2 - 1, sim_duration_units/2 + 1) # Y축 범위도 충분히 넓게
    ax_stars.set_aspect('equal', adjustable='box')
    ax_stars.axis('off')
    ax_stars.set_title("별들의 상대적 위치", color='white')

    # 광도 곡선 설정
    ax_curve.set_xlabel("시간 (상대 단위)", color='white')
    ax_curve.set_ylabel("배경 별의 상대 밝기 (확대율)", color='white')
    ax_curve.set_title("미세중력렌즈 광도 곡선", color='white')
    ax_curve.grid(True, linestyle='--', alpha=0.7, color='gray')
    ax_curve.set_facecolor('#333333') # 어두운 배경
    ax_curve.tick_params(colors='white') # 축 눈금 색상
    ax_curve.spines['left'].set_color('white') # 축 테두리 색상
    ax_curve.spines['bottom'].set_color('white')

    # 초기 플롯 객체
    # 별들
    source_point, = ax_stars.plot([], [], 'o', color='gold', markersize=20, label="배경 별")
    lens_point, = ax_stars.plot([], [], 'o', color='skyblue', markersize=15, label="렌즈 별")
    planet_point, = ax_stars.plot([], [], 'o', color='gray', markersize=8, label="행성")
    einstein_ring_patch = plt.Circle((0, 0), RE, color='white', fill=False, linestyle='--', linewidth=0.8, alpha=0.6)
    ax_stars.add_patch(einstein_ring_patch)

    # 광도 곡선
    line_lc, = ax_curve.plot([], [], color='lime')

    # 광도 곡선 데이터 저장 리스트 (FuncAnimation 내부에서 업데이트)
    lc_times = []
    lc_magnifications = []

    def update(frame):
        # 렌즈 별의 X 위치 (시뮬레이션 범위 -sim_duration_units/2 에서 sim_duration_units/2 까지 이동)
        lens_x_current = -sim_duration_units / 2 + (frame / (sim_total_frames - 1)) * sim_duration_units
        
        # 배경 별의 위치 (중앙 고정)
        source_x, source_y = 0.0, 0.0
        
        # 렌즈 별과 배경 별 사이의 거리 (u)
        u = abs(lens_x_current - source_x)
        current_magnification = calculate_magnification(u)

        # 행성의 공전 위치 계산 (렌즈 별을 중심으로, 같은 횡단 평면 내에서)
        planet_angle = frame * planet_orbit_speed_rad_per_frame # 프레임당 각도 증가
        planet_x_offset = planet_distance_re * np.cos(planet_angle)
        planet_y_offset = planet_distance_re * np.sin(planet_angle) # 같은 평면 내 공전

        # 시각화 업데이트
        source_point.set_data(source_x, source_y)
        lens_point.set_data(lens_x_current, 0) # 렌즈 별은 X축만 따라 이동
        planet_point.set_data(lens_x_current + planet_x_offset, planet_y_offset) # 행성은 렌즈 별을 중심으로 공전
        
        einstein_ring_patch.center = (lens_x_current, 0) # 아인슈타인 링도 렌즈 별 따라 이동

        # 텍스트 업데이트 (별 라벨은 한 번만 그리는 것이 좋음)
        if frame == 0:
            ax_stars.text(source_x + 0.2, source_y + 0.2, "배경 별", color='gold', fontsize=10)
            ax_stars.text(lens_x_current + 0.2, 0 + 0.2, "렌즈 별", color='skyblue', fontsize=10)
            ax_stars.text(lens_x_current + RE + 0.1, 0.5, "$R_E$", color='white', fontsize=10, ha='left', va='center')


        # 광도 곡선 데이터 업데이트
        lc_times.append(frame) # 시간 대신 프레임 번호를 사용 (상대 시간)
        lc_magnifications.append(current_magnification)

        line_lc.set_data(lc_times, lc_magnifications)
        ax_curve.set_xlim(0, sim_total_frames)
        # Y축 범위 조정: 최소 1배부터 최대 확대율까지 + 여유 공간
        min_mag = 1.0 
        max_mag_in_data = max(lc_magnifications) if lc_magnifications else 1.0
        ax_curve.set_ylim(bottom=0.95, top=max(max_mag_in_data * 1.1, 2.0)) # 최소 2.0까지 보이게 (일반적인 피크)

        return source_point, lens_point, planet_point, einstein_ring_patch, line_lc # 업데이트된 객체 반환

    ani = FuncAnimation(fig, update, frames=sim_total_frames, interval=sim_frame_interval_ms, blit=True, repeat=False)

    # GIF로 저장 (Streamlit에서 표시하기 위함)
    gif_path = "microlensing_animation.gif"
    ani.save(gif_path, writer='pillow', fps=1000/sim_frame_interval_ms) # interval을 fps로 변환
    
    plt.close(fig) # 그래프 객체 닫기

    # GIF 파일을 base64로 인코딩하여 직접 임베드
    with open(gif_path, "rb") as f:
        contents = f.read()
        data_url = base64.b64encode(contents).decode("utf-8")
    
    # 세션 상태에 저장하여 캐싱 후에도 사용 가능하게
    st.session_state.animation_created = True
    st.session_state.animation_path = data_url
    st.session_state.light_curve_data['time'] = lc_times
    st.session_state.light_curve_data['magnification'] = lc_magnifications
    
    return data_url

# --- 애니메이션 표시 영역 ---
st.markdown("---")

if st.session_state.animation_created and st.session_state.animation_path:
    col_viz_gif, col_curve_static = st.columns([2, 3])
    
    with col_viz_gif:
        st.subheader("렌즈 효과 시뮬레이션")
        st.image(f"data:image/gif;base64,{st.session_state.animation_path}", use_column_width=True)
        st.caption("렌즈 별이 배경 별 앞을 지나가면서 빛이 휘어지는 모습을 시뮬레이션합니다.")
    
    with col_curve_static:
        st.subheader("광도 곡선 (이벤트 전체)")
        # FuncAnimation에서 최종적으로 계산된 전체 광도 곡선 데이터 표시
        final_times = st.session_state.light_curve_data['time']
        final_mags = st.session_state.light_curve_data['magnification']

        if final_times and final_mags:
            fig_final_curve, ax_final_curve = plt.subplots(figsize=(8, 6))
            ax_final_curve.plot(final_times, final_mags, color='lime')
            ax_final_curve.set_xlabel("시간 (상대 단위)", color='white')
            ax_final_curve.set_ylabel("배경 별의 상대 밝기 (확대율)", color='white')
            ax_final_curve.set_title("미세중력렌즈 광도 곡선 (전체 이벤트)", color='white')
            ax_final_curve.grid(True, linestyle='--', alpha=0.7, color='gray')
            ax_final_curve.set_facecolor('#333333')
            ax_final_curve.tick_params(colors='white')
            ax_final_curve.spines['left'].set_color('white')
            ax_final_curve.spines['bottom'].set_color('white')

            min_mag = 1.0 
            max_mag_in_data = max(final_mags) if final_mags else 1.0
            ax_final_curve.set_ylim(bottom=0.95, top=max(max_mag_in_data * 1.1, 2.0))
            ax_final_curve.set_xlim(left=0, right=sim_total_frames)

            st.pyplot(fig_final_curve)
            plt.close(fig_final_curve)
else:
    st.info("시뮬레이션 '실행' 버튼을 눌러 애니메이션을 생성하고 확인하세요.")
