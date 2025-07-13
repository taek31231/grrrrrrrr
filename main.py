import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os
import base64
import tempfile 

# --- 상수 및 초기 설정 ---
RE = 1.0 # 아인슈타인 반지름을 단위로 가정 (시뮬레이션의 단순화를 위함)

# --- 미세중력렌즈 확대율 함수 (단일 렌즈 모델) ---
def calculate_magnification(u):
    """
    단일 렌즈 미세중력렌즈 효과의 확대율을 계산합니다.
    u: 배경 별과 렌즈 별 사이의 거리 (아인슈타인 반지름으로 정규화된 값)
    """
    # u가 0에 매우 가까워지면 무한대로 발산할 수 있으므로, 하한값을 둠
    if u < 0.01: # 매우 작은 충격 매개변수 (피크 확대율 제한)
        u = 0.01
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))

# --- 애니메이션 생성 및 표시 함수 ---
# @st.cache_data는 함수 인자가 변경될 때만 다시 실행되도록 합니다.
@st.cache_data(show_spinner=False) # 스피너는 호출하는 곳에서 제어
def create_and_display_animation(
    sim_total_frames, sim_duration_units, sim_frame_interval_ms,
    planet_distance_re, planet_orbit_speed_rad_per_frame
):
    fig, (ax_stars, ax_curve) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={'width_ratios': [1, 2]})
    
    # 별 시각화 설정
    ax_stars.set_facecolor('black')
    # 렌즈 별의 횡단 경로를 고려하여 X, Y 축 범위를 넓게 잡음
    plot_limit = sim_duration_units / 2 + max(RE, planet_distance_re) + 1 # RE와 행성 거리 고려
    ax_stars.set_xlim(-plot_limit, plot_limit)
    ax_stars.set_ylim(-plot_limit, plot_limit) 
    ax_stars.set_aspect('equal', adjustable='box')
    ax_stars.axis('off')
    ax_stars.set_title("별들의 상대적 위치", color='white')

    # 광도 곡선 설정
    ax_curve.set_xlabel("시간 (프레임)", color='white')
    ax_curve.set_ylabel("배경 별의 상대 밝기 (확대율)", color='white')
    ax_curve.set_title("미세중력렌즈 광도 곡선", color='white')
    ax_curve.grid(True, linestyle='--', alpha=0.7, color='gray')
    ax_curve.set_facecolor('#333333') # 어두운 배경
    ax_curve.tick_params(colors='white') # 축 눈금 색상
    ax_curve.spines['left'].set_color('white') # 축 테두리 색상
    ax_curve.spines['bottom'].set_color('white')

    # 초기 플롯 객체
    # 별들
    source_x, source_y = 0.0, 0.0 # 배경 별은 항상 중앙
    source_point, = ax_stars.plot([], [], 'o', color='gold', markersize=20, label="배경 별")
    lens_point, = ax_stars.plot([], [], 'o', color='skyblue', markersize=15, label="렌즈 별")
    planet_point, = ax_stars.plot([], [], 'o', color='gray', markersize=8, label="행성")
    einstein_ring_patch = plt.Circle((0, 0), RE, color='white', fill=False, linestyle='--', linewidth=0.8, alpha=0.6)
    ax_stars.add_patch(einstein_ring_patch)

    # 배경 별 텍스트는 한 번만 추가 (움직이지 않으므로)
    ax_stars.text(source_x + 0.2, source_y + 0.2, "배경 별", color='gold', fontsize=10)


    # 광도 곡선
    line_lc, = ax_curve.plot([], [], color='lime')

    # 광도 곡선 데이터 저장 리스트 (FuncAnimation 내부에서 업데이트)
    lc_times = []
    lc_magnifications = []

    def update(frame):
        # 렌즈 별의 X 위치 (시뮬레이션 범위 -sim_duration_units/2 에서 sim_duration_units/2 까지 이동)
        lens_x_current = -sim_duration_units / 2 + (frame / (sim_total_frames - 1)) * sim_duration_units
        
        # 렌즈 별과 배경 별 사이의 거리 (u_lens) 및 기본 확대율 (main_magnification)
        u_lens = abs(lens_x_current - source_x)
        main_magnification = calculate_magnification(u_lens)

        # 행성의 공전 위치 계산 (렌즈 별을 중심으로, 같은 횡단 평면 내에서)
        planet_angle = frame * planet_orbit_speed_rad_per_frame # 프레임당 각도 증가
        planet_x_offset = planet_distance_re * np.cos(planet_angle)
        planet_y_offset = planet_distance_re * np.sin(planet_angle) # 같은 평면 내 공전

        planet_display_x = lens_x_current + planet_x_offset
        planet_display_y = planet_y_offset 

        # --- 행성으로 인한 추가 확대율 계산 ---
        # 배경 별과 행성 사이의 거리 (이것이 행성 렌즈에 대한 '충격 매개변수' 역할을 함)
        u_planet_to_source = np.sqrt((planet_display_x - source_x)**2 + (planet_display_y - source_y)**2)
        
        # 행성의 영향이 시작되는 '유효 반지름' (이 값을 조절하여 피크 너비와 발생 시점 조절)
        # RE의 50% 정도로 설정하여 행성 피크가 나타날 확률을 높임
        planet_event_radius = 0.5 * RE 
        
        # 행성으로 인한 최대 확대율 기여도 (이 값으로 행성 피크의 높이 조절)
        # 메인 피크의 높이(최대 2.0 이상)를 고려하여 꽤 높게 설정해야 시각적으로 구분됨
        max_planet_magnification_contribution = 1.0 # 예를 들어, 최대 1.0배 추가 밝기

        additional_magnification = 0.0
        # 행성이 배경 별에 충분히 가까워지면 추가 확대율 발생
        if u_planet_to_source < planet_event_radius:
            # 행성과의 거리가 가까워질수록 확대율이 증가하도록 (단순한 선형/2차 함수)
            # 여기서는 2차 함수 형태를 사용하여 피크 중심에서 가장 높고 가장자리로 갈수록 부드럽게 감소
            # 1 - (거리/반지름)^2 형태: 거리가 0이면 1, 반지름과 같으면 0
            factor = 1 - (u_planet_to_source / planet_event_radius)**2
            additional_magnification = max_planet_magnification_contribution * factor
            # 확대율이 음수가 되지 않도록 최소 0을 보장
            additional_magnification = max(0.0, additional_magnification)

        # 최종 확대율은 주 렌즈(별)의 확대율에 행성의 추가 확대율을 더한 값
        current_magnification = main_magnification + additional_magnification

        # 시각화 업데이트: 단일 값을 리스트로 감싸서 전달
        source_point.set_data([source_x], [source_y])
        lens_point.set_data([lens_x_current], [0]) 
        planet_point.set_data([planet_display_x], [planet_display_y])
        
        einstein_ring_patch.center = (lens_x_current, 0) 

        # 광도 곡선 데이터 업데이트
        lc_times.append(frame) 
        lc_magnifications.append(current_magnification)

        line_lc.set_data(lc_times, lc_magnifications)
        ax_curve.set_xlim(0, sim_total_frames)
        
        # Y축 범위 조정: 최소 1배부터 최대 확대율까지 + 여유 공간
        min_mag = 1.0 
        max_mag_in_data = max(lc_magnifications) if lc_magnifications else 1.0
        ax_curve.set_ylim(bottom=0.95, top=max(max_mag_in_data * 1.1, 2.0)) 

        return source_point, lens_point, planet_point, einstein_ring_patch, line_lc

    # FuncAnimation 호출에서 blit=True를 False로 변경하거나 제거하여 테스트
    # blit=True를 제거하는 것이 초기 테스트 시 더 안전합니다.
    ani = FuncAnimation(fig, update, frames=sim_total_frames, interval=sim_frame_interval_ms, blit=False, repeat=False)

    # --- GIF로 저장 (tempfile 사용) ---
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmpfile:
        gif_path = tmpfile.name
    
    # pillow writer가 필요할 때 다음과 같이 명시적으로 설정
    ani.save(gif_path, writer='pillow', fps=1000/sim_frame_interval_ms) # interval을 fps로 변환
    
    plt.close(fig) # 그래프 객체 닫기 (메모리 해제)

    # GIF 파일을 base64로 인코딩하여 직접 임베드
    with open(gif_path, "rb") as f:
        contents = f.read()
        data_url = base64.b64encode(contents).decode("utf-8")
    
    # 임시 파일 삭제 (선택 사항이지만 깔끔한 관리를 위해 권장)
    os.remove(gif_path)
    
    # 최종 광도 곡선 데이터를 세션 상태에 저장하여 나중에 정적 그래프로 그릴 수 있도록 함
    st.session_state.light_curve_data['time'] = lc_times
    st.session_state.light_curve_data['magnification'] = lc_magnifications
    
    return data_url


# --- Streamlit 앱 시작 ---
st.set_page_config(layout="wide", page_title="미세중력렌즈 시뮬레이터")

st.title("🔭 미세중력렌즈 시각화 및 시뮬레이터")

st.markdown("""
이 앱은 **미세중력렌즈(Microlensing)** 현상을 시각적으로 탐색하고 이해할 수 있도록 돕습니다.
우리와 배경 별 사이에 있는 **렌즈 별**의 중력에 의해 먼 **배경 별**의 빛이 휘어져
밝기가 일시적으로 증가하는 현상을 시뮬레이션합니다.

**사용 방법:**
1.  사이드바에서 시뮬레이션 설정을 조절합니다.
2.  **'시뮬레이션 실행 및 애니메이션 생성' 버튼**을 눌러 이벤트 시뮬레이션을 시작하고 광도 곡선 피크를 확인하세요.
3.  생성된 애니메이션은 부드러운 움직임을 보여줍니다.
""")

st.header("✨ 시뮬레이션 제어 및 설정")

# --- 모든 st.session_state 변수 초기화 (NameError 방지) ---
if 'animation_created' not in st.session_state:
    st.session_state.animation_created = False
if 'animation_path_base64' not in st.session_state: # base64 인코딩된 문자열 저장
    st.session_state.animation_path_base64 = None
if 'light_curve_data' not in st.session_state:
    st.session_state.light_curve_data = {'time': [], 'magnification': []}

# 슬라이더의 기본값들을 session_state에 미리 초기화 (슬라이더 정의보다 먼저)
if 'sim_total_frames' not in st.session_state:
    st.session_state.sim_total_frames = 200
if 'sim_duration_units' not in st.session_state:
    st.session_state.sim_duration_units = 10.0
if 'sim_frame_interval_ms' not in st.session_state:
    st.session_state.sim_frame_interval_ms = 50
if 'planet_distance_re' not in st.session_state:
    st.session_state.planet_distance_re = 0.5
if 'planet_orbit_speed_rad_per_frame' not in st.session_state:
    st.session_state.planet_orbit_speed_rad_per_frame = 0.05
# --- 세션 상태 초기화 끝 ---


col_buttons = st.columns(3)
with col_buttons[0]:
    if st.button("▶️ 시뮬레이션 실행 및 애니메이션 생성"):
        st.session_state.animation_created = False # 애니메이션 재생성 트리거
        st.session_state.animation_path_base64 = None
        st.session_state.light_curve_data = {'time': [], 'magnification': []} # 데이터 초기화
        
        # 애니메이션 생성 함수 호출 (캐싱되어 있으므로 설정값 변경 없으면 빠르게 반환)
        # 이 시점에서 생성 메시지를 표시하기 위해 스피너 사용
        with st.spinner("애니메이션을 생성 중입니다... ✨ (설정값에 따라 시간이 걸릴 수 있습니다)"):
            data_url = create_and_display_animation( 
                sim_total_frames=st.session_state.sim_total_frames,
                sim_duration_units=st.session_state.sim_duration_units,
                sim_frame_interval_ms=st.session_state.sim_frame_interval_ms,
                planet_distance_re=st.session_state.planet_distance_re,
                planet_orbit_speed_rad_per_frame=st.session_state.planet_orbit_speed_rad_per_frame
            )
            st.session_state.animation_path_base64 = data_url
            st.session_state.animation_created = True
        st.success("애니메이션 생성 완료! 아래에서 확인하세요.")
        st.rerun() # UI 업데이트를 위해 앱을 다시 로드

with col_buttons[1]:
    if st.button("🔄 시뮬레이션 초기화"):
        st.session_state.animation_created = False
        st.session_state.animation_path_base64 = None
        st.session_state.light_curve_data = {'time': [], 'magnification': []}
        st.rerun() # 앱을 처음부터 다시 로드하여 초기 상태로 만듦


st.sidebar.header("⚙️ 시뮬레이션 설정")

# 슬라이더 정의 (이전 섹션에서 미리 session_state에 초기화되었으므로 안전하게 참조 가능)
st.session_state.sim_total_frames = st.sidebar.slider(
    "총 시뮬레이션 프레임 수",
    min_value=100,
    max_value=500,
    value=st.session_state.sim_total_frames, # 초기값을 session_state에서 가져옴
    step=50,
    help="애니메이션의 전체 프레임 수를 조절합니다. 많을수록 부드러워지지만 생성 시간이 길어집니다."
)
st.session_state.sim_duration_units = st.sidebar.slider(
    "렌즈 별 횡단 범위 (아인슈타인 반지름)",
    min_value=5.0,
    max_value=20.0,
    value=st.session_state.sim_duration_units,
    step=1.0,
    help="렌즈 별이 배경 별 앞을 지나가는 총 거리를 조절합니다. (예: 10은 -5RE에서 +5RE까지)"
)
st.session_state.sim_frame_interval_ms = st.sidebar.slider(
    "프레임 간 간격 (ms)",
    min_value=20,
    max_value=200,
    value=st.session_state.sim_frame_interval_ms,
    step=10,
    help="애니메이션 프레임 간의 시간 간격입니다. 작을수록 빠릅니다."
)

st.session_state.planet_distance_re = st.sidebar.slider(
    "행성-렌즈 별 거리 (아인슈타인 반지름 대비)",
    min_value=0.1,
    max_value=2.0,
    value=st.session_state.planet_distance_re,
    step=0.1,
    help="렌즈 별로부터 행성의 거리를 조절합니다. 아인슈타인 반지름(RE)에 비례합니다."
)
st.session_state.planet_orbit_speed_rad_per_frame = st.sidebar.slider(
    "행성 공전 속도 (프레임당 라디안)",
    min_value=0.01,
    max_value=0.2,
    value=st.session_state.planet_orbit_speed_rad_per_frame,
    step=0.01,
    help="행성이 렌즈 별 주위를 공전하는 속도입니다. 값이 클수록 빠르게 공전합니다."
)

# --- 애니메이션 표시 영역 ---
st.markdown("---")

# 애니메이션이 생성되었으면 GIF와 최종 광도 곡선 표시
if st.session_state.animation_created and st.session_state.animation_path_base64:
    col_viz_gif, col_curve_static = st.columns([2, 3])
    
    with col_viz_gif:
        st.subheader("렌즈 효과 시뮬레이션")
        # 경고 메시지 처리를 위해 use_column_width 대신 use_container_width 사용 (Streamlit 최신 버전)
        st.image(f"data:image/gif;base64,{st.session_state.animation_path_base64}", use_container_width=True) 
        st.caption("렌즈 별이 배경 별 앞을 지나가면서 빛이 휘어지는 모습을 시뮬레이션합니다.")
    
    with col_curve_static:
        st.subheader("광도 곡선 (이벤트 전체)")
        # FuncAnimation에서 최종적으로 계산된 전체 광도 곡선 데이터 표시
        final_times = st.session_state.light_curve_data['time']
        final_mags = st.session_state.light_curve_data['magnification']

        if final_times and final_mags:
            fig_final_curve, ax_final_curve = plt.subplots(figsize=(8, 6))
            ax_final_curve.plot(final_times, final_mags, color='lime')
            ax_final_curve.set_xlabel("시간 (프레임)", color='white')
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
            ax_final_curve.set_xlim(left=0, right=st.session_state.sim_total_frames) # X축 범위도 설정

            st.pyplot(fig_final_curve)
            plt.close(fig_final_curve)
else:
    st.info("사이드바에서 설정을 조절하고 '시뮬레이션 실행 및 애니메이션 생성' 버튼을 눌러 애니메이션을 확인하세요.")
