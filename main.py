import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import time
import math

# --- 상수 및 초기 설정 ---
# 아인슈타인 반지름을 단위로 가정 (시뮬레이션의 단순화를 위함)
RE = 1.0 

# --- 미세중력렌즈 확대율 함수 (단일 렌즈 모델) ---
def calculate_magnification(u):
    """
    단일 렌즈 미세중력렌즈 효과의 확대율을 계산합니다.
    u: 배경 별과 렌즈 별 사이의 거리 (아인슈타인 반지름으로 정규화된 값)
    """
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))

# --- Streamlit 앱 시작 ---
st.set_page_config(layout="wide", page_title="미세중력렌즈 시뮬레이터")

st.title("🔭 미세중력렌즈 시각화 및 시뮬레이터")

st.markdown("""
이 앱은 **미세중력렌즈(Microlensing)** 현상을 시각적으로 탐색하고 이해할 수 있도록 돕습니다.
렌즈 별의 중력에 의해 먼 배경 별의 빛이 휘어져 밝기가 일시적으로 변하는 현상을 시뮬레이션합니다.

**사용 방법:**
1.  **'렌즈 별 횡단 위치' 슬라이더**를 좌우로 움직여 렌즈 별이 배경 별 앞을 지나가는 위치를 조절해보세요.
2.  렌즈 별 주위를 **공전하는 행성**의 모습을 관찰해보세요.
3.  아래 **광도 곡선 그래프**가 실시간으로 어떻게 변화하는지 확인해보세요.
    (현재 시뮬레이션에서는 행성의 중력 효과는 광도 곡선에 반영되지 않고 시각적으로만 나타납니다.)
""")

st.sidebar.header("⚙️ 시뮬레이션 설정")
# 렌즈 별의 초기 X 위치 (슬라이더로 조절)
lens_x_initial = st.sidebar.slider(
    "렌즈 별 횡단 위치 (상대 거리)",
    min_value=-5.0,
    max_value=5.0,
    value=0.0,
    step=0.1,
    help="렌즈 별이 배경 별에 대해 상대적으로 얼마나 떨어져 있는지 조절합니다. 0에 가까울수록 정렬됩니다."
)

# 행성 설정
planet_distance = st.sidebar.slider(
    "행성-렌즈 별 거리 (상대 단위)",
    min_value=0.1,
    max_value=2.0,
    value=0.5,
    step=0.1,
    help="렌즈 별로부터 행성의 거리를 조절합니다."
)
planet_orbit_speed = st.sidebar.slider(
    "행성 공전 속도",
    min_value=0.05,
    max_value=0.5,
    value=0.1,
    step=0.01,
    help="행성이 렌즈 별 주위를 공전하는 속도를 조절합니다."
)

# 시뮬레이션 속도 조절
animation_speed = st.sidebar.slider(
    "애니메이션 속도",
    min_value=0.01,
    max_value=0.1,
    value=0.05,
    step=0.01,
    help="애니메이션 업데이트 간격을 조절합니다 (값이 작을수록 빠릅니다)."
)

# --- 시뮬레이션 및 광도 곡선 영역 ---
st.header("✨ 실시간 시뮬레이션")

# Matplotlib 그래프를 위한 컨테이너 (애니메이션 업데이트용)
plot_container = st.empty()

# 광도 곡선 데이터를 저장할 리스트
time_history = []
magnification_history = []
max_history_points = 200 # 그래프에 표시할 최대 데이터 포인트 수

# 초기 시간
start_time = time.time()
frame_count = 0

# --- 시뮬레이션 루프 ---
while True:
    current_time_for_orbit = time.time() - start_time
    
    # 행성의 공전 위치 계산
    planet_angle = current_time_for_orbit * planet_orbit_speed
    planet_x_offset = planet_distance * np.cos(planet_angle)
    planet_y_offset = planet_distance * np.sin(planet_angle)

    # 렌즈 별의 현재 X 위치 (슬라이더 값)
    lens_x = lens_x_initial

    # 배경 별의 위치 (고정)
    source_x = 0
    source_y = 0
    
    # 렌즈 별과 배경 별 사이의 거리 (u) 계산
    # 여기서는 Y축 움직임이 없으므로 X축 거리만 고려
    u = abs(lens_x - source_x) # 아인슈타인 반지름 단위
    
    # 0으로 나누는 오류 방지 (u가 0에 가까워질 때)
    if u < 0.001: 
        u = 0.001
    
    current_magnification = calculate_magnification(u)

    # 광도 곡선 데이터 업데이트
    time_history.append(frame_count * animation_speed) # 단순 시간 경과
    magnification_history.append(current_magnification)

    # 데이터 포인트 제한 (그래프가 너무 길어지는 것을 방지)
    if len(time_history) > max_history_points:
        time_history.pop(0)
        magnification_history.pop(0)

    # --- 시각화 (Matplotlib) ---
    with plot_container.container():
        # 첫 번째 열: 별들의 상대적 위치 시각화
        col_viz, col_curve = st.columns([2, 3]) # 시각화와 그래프의 비율 조정

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
            planet_display_x = lens_x + planet_x_offset
            planet_display_y = 0 + planet_y_offset # 2D 평면이므로 Y는 0으로 고정
            ax_stars.plot(planet_display_x, planet_display_y, 'o', color='gray', markersize=8, label="행성")
            
            # 아인슈타인 링 (렌즈 별 주위 원) - 시각적 가이드
            einstein_ring = plt.Circle((lens_x, 0), RE, color='white', fill=False, linestyle='--', linewidth=0.8, alpha=0.6)
            ax_stars.add_patch(einstein_ring)
            ax_stars.text(lens_x + RE + 0.1, 0, "$R_E$", color='white', fontsize=10, ha='left', va='center')


            ax_stars.set_xlim(-5, 5)
            ax_stars.set_ylim(-3, 3) # Y축 범위는 고정
            ax_stars.set_aspect('equal', adjustable='box')
            ax_stars.axis('off') # 축 숨기기
            st.pyplot(fig_stars)
            plt.close(fig_stars) # Matplotlib 경고 방지

        with col_curve:
            st.subheader("광도 곡선")
            fig_curve, ax_curve = plt.subplots(figsize=(8, 6))
            ax_curve.plot(time_history, magnification_history, color='lime')
            ax_curve.set_xlabel("시간 경과 (상대 단위)")
            ax_curve.set_ylabel("배경 별의 상대 밝기 (확대율)")
            ax_curve.set_title("미세중력렌즈 광도 곡선")
            ax_curve.grid(True, linestyle='--', alpha=0.7)
            # Y축 범위는 확대율 최대값에 따라 유동적으로 설정
            ax_curve.set_ylim(bottom=0.9, top=max(magnification_history) * 1.2 if magnification_history else 2.0)
            ax_curve.set_xlim(left=time_history[0] if time_history else 0, 
                              right=time_history[-1] + 1 if time_history else 10)
            st.pyplot(fig_curve)
            plt.close(fig_curve) # Matplotlib 경고 방지
        
        # 작은 설명 추가
        st.caption(f"현재 렌즈-배경 별 상대 거리 (u): {u:.2f}, 현재 확대율: {current_magnification:.2f}")

    frame_count += 1
    time.sleep(animation_speed) # 애니메이션 속도 조절
