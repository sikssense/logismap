import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
import streamlit as st
from streamlit_folium import folium_static
import os
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="로지스 수요처 맵",
    page_icon="🏢",
    layout="wide"
)

# 세션 상태 관리를 위한 변수 초기화
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'search_clicked' not in st.session_state:
    st.session_state.search_clicked = False

# 검색 버튼 클릭 시 호출될 함수
def on_search_clicked():
    st.session_state.search_clicked = True

# 제목
st.title("🏢 로지스 수요처 맵")

# 데이터 전처리
def process_data(df):
    # 위도/경도 컬럼 확인
    if '위도' in df.columns and '경도' in df.columns:
        # 컬럼 이름 통일
        if 'latitude' not in df.columns:
            df['latitude'] = df['위도']
        if 'longitude' not in df.columns:
            df['longitude'] = df['경도']
    
    # 사업자등록번호 문자열로 변환 (소수점 문제 해결)
    if '사업자등록번호' in df.columns:
        df['사업자등록번호'] = df['사업자등록번호'].astype(str)
        # 소수점 제거 및 숫자만 추출
        df['사업자등록번호'] = df['사업자등록번호'].apply(lambda x: x.split('.')[0] if '.' in x else x)
        
    # 유효한 좌표만 필터링 (경고 메시지 제거)
    df_with_coords = df[df['latitude'].notna() & df['longitude'].notna()].copy()
    
    # 한국 지역 내 좌표만 필터링 (위도 33~38.5, 경도 124~132) - 경고 메시지 제거
    korea_coords = (df_with_coords['latitude'] >= 33) & (df_with_coords['latitude'] <= 38.5) & \
                  (df_with_coords['longitude'] >= 124) & (df_with_coords['longitude'] <= 132)
    
    df_with_coords = df_with_coords[korea_coords].reset_index(drop=True)
    
    # 주소에서 시도/시군구 정보 추출 (필요한 경우)
    if 'sido' not in df_with_coords.columns and '한글주소' in df_with_coords.columns:
        # 주소에서 시도 추출
        sido_pattern = '(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)'
        df_with_coords['sido'] = df_with_coords['한글주소'].str.extract(f'{sido_pattern}', expand=False)
        
        # 시군구 패턴 (예: 강남구, 용산구, 수원시, 부천시 등)
        sigungu_pattern = '([가-힣]+시|[가-힣]+구|[가-힣]+군)'
        df_with_coords['sigungu'] = df_with_coords['한글주소'].str.extract(sigungu_pattern, expand=False)
    
    return df_with_coords

@st.cache_data(show_spinner=False)
def load_company_data():
    # 실제 데이터 파일 경로
    file_path = "로지스_수요처데이터_240906_중복제거_수정.xlsx"  # 업데이트된 파일명
    
    try:
        # 데이터 로드 (성공 메시지 제거)
        df = pd.read_excel(file_path, dtype={'사업자등록번호': str})  # 사업자등록번호를 문자열로 로드
        
        # 데이터 처리
        return process_data(df)
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()  # 빈 데이터프레임 반환

# 메인 앱 코드
def main():
    # 데이터 로드 (로딩 메시지 숨김)
    with st.spinner("데이터를 불러오는 중..."):
        df = load_company_data()
    
    if len(df) == 0:
        st.error("데이터를 로드할 수 없습니다. 파일 경로를 확인해주세요.")
        return
    
    # 안내 문구 제거함
    
    # ===== 상단 검색 및 필터링 옵션 =====
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 검색 필드를 form으로 감싸기
    with st.form(key='search_form'):
        # 순서 변경: 시도/군구, 기업규모, 신용등급, 통합검색
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])  # 컬럼 크기 조정, 검색버튼 추가
        
        with col1:
            # 시도/군구 선택 (드롭다운)
            if 'sido' in df.columns and df['sido'].notna().sum() > 0:
                regions = ['전체'] + sorted(df['sido'].dropna().unique().tolist())
                selected_region = st.selectbox("시도/군구", regions, key="sido", help="지역을 선택하세요")
                
                # 시도 선택 시 하위 시군구 필터링을 위한 변수
                if selected_region != '전체' and 'sigungu' in df.columns:
                    districts = ['전체'] + sorted(df[df['sido'] == selected_region]['sigungu'].dropna().unique().tolist())
                else:
                    districts = ['전체']
            else:
                st.text("시도/군구")
                selected_region = '전체'
                districts = ['전체']
            
            # 시도 선택 시 하위 시군구 선택 옵션 표시
            if selected_region != '전체' and 'sigungu' in df.columns:
                selected_district = st.selectbox("", districts, key="sigungu", label_visibility="collapsed")
            else:
                selected_district = '전체'
        
        with col2:
            # 기업 규모 (이미 문자열 형태로 되어 있다고 가정)
            if '기업규모구분' in df.columns and df['기업규모구분'].notna().sum() > 0:
                company_sizes = ['전체'] + sorted(df['기업규모구분'].dropna().unique().tolist())
                selected_size = st.selectbox("기업규모", company_sizes)
            else:
                st.text("기업규모")
                selected_size = '전체'
        
        with col3:
            # 신용 등급
            if '신용등급' in df.columns and df['신용등급'].notna().sum() > 0:
                credit_ratings = ['전체'] + sorted(df['신용등급'].dropna().unique().tolist())
                selected_credit = st.selectbox("신용등급", credit_ratings)
            else:
                st.text("신용등급")
                selected_credit = '전체'
        
        with col4:
            search_term = st.text_input("통합검색", placeholder="기업명, 업종, 업태, 산업분류 등", help="검색어를 입력하세요")
        
        # 검색 버튼을 같은 행에 배치
        with col5:
            search_submit = st.form_submit_button("검색", on_click=on_search_clicked)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 검색 버튼 클릭 시 필터링 실행
    if st.session_state.search_clicked:
        # 로딩 상태 표시
        with st.spinner("데이터를 필터링하고 있습니다..."):
            # ===== 필터링 로직 적용 =====
            filtered_df = df.copy()
            
            # 시도/군구 필터링 (순서 변경에 맞춰 필터링 순서도 변경)
            if selected_region != '전체' and 'sido' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['sido'] == selected_region]
                
                if selected_district != '전체' and 'sigungu' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['sigungu'] == selected_district]
            
            # 기업규모 필터링
            if selected_size != '전체' and '기업규모구분' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['기업규모구분'] == selected_size]
            
            # 신용등급 필터링
            if selected_credit != '전체' and '신용등급' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['신용등급'] == selected_credit]
                
            # 통합 검색어 적용
            if search_term:
                search_mask = pd.Series([False] * len(filtered_df))
                # 다양한 열에서 검색어 찾기
                text_columns = [col for col in filtered_df.columns if filtered_df[col].dtype == 'object']
                for column in text_columns:
                    search_mask = search_mask | filtered_df[column].astype(str).str.contains(search_term, case=False, na=False, regex=True)
                filtered_df = filtered_df[search_mask]
            
            # 세션 상태에 필터링 결과 저장
            st.session_state.filtered_data = filtered_df
        
        # ===== 필터링 결과 표시 =====
        filtered_df = st.session_state.filtered_data  # 세션 상태의 필터링 데이터 사용
        st.markdown(f"<h4>검색 결과: {len(filtered_df)}개의 기업 데이터</h4>", unsafe_allow_html=True)
        
    elif st.session_state.filtered_data is not None:
        # 이전 검색 결과가 있을 경우 표시
        filtered_df = st.session_state.filtered_data
        st.markdown(f"<h4>검색 결과: {len(filtered_df)}개의 기업 데이터</h4>", unsafe_allow_html=True)
    else:
        st.info("검색 버튼을 클릭하여 데이터를 필터링하세요.")
        return
    
    # ===== 지도 옵션 (사이드바에 배치) =====
    st.sidebar.header("지도 시각화 옵션")
    
    # 지도 스타일 선택 (타일 속성 추가) - Google 지도 스타일 추가
    tile_options = {
        "Google 지도 (표준)": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "Google 위성 지도": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "Google 하이브리드": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "Google 지형도": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB Positron (밝은 테마)": "CartoDB positron",
        "CartoDB Dark Matter (어두운 테마)": "CartoDB dark_matter"
    }
    
    selected_style = st.sidebar.selectbox("지도 스타일", list(tile_options.keys()), index=0)  # 기본값을 Google 지도로 설정
    
    # 마커 스타일 선택
    marker_style = st.sidebar.radio(
        "마커 스타일",
        ['기본 마커', '원형 마커']
    )
    
    # 클러스터링 옵션
    use_clustering = st.sidebar.checkbox("클러스터링 사용", value=True)  # 기존대로 True 유지
    if use_clustering:
        cluster_radius = st.sidebar.slider("클러스터링 반경", 10, 100, 50)
        min_cluster_size = st.sidebar.slider("최소 클러스터 크기", 2, 10, 2)
    
    # 마커 색상 기준 선택
    color_options = ['기업 규모', '신용등급', '현금흐름등급', '업종명']
    color_by = st.sidebar.radio("마커 색상 기준", color_options)
    
    # 색상 선택 기준에 따른 컬러맵 설정
    if color_by == '기업 규모':
        color_field = '기업규모구분'
        # 기업 규모별 색상
        company_colors = {
            '대기업': 'red',
            '중견기업': 'blue',
            '중소기업': 'green',
            '기타': 'gray'
        }
        # 데이터에 존재하는 값만 사용
        color_map = {size: company_colors.get(size, 'gray') for size in filtered_df['기업규모구분'].dropna().unique()}
    elif color_by == '신용등급':
        color_field = '신용등급'
        # 신용등급에 따른 색상 매핑 (AAA부터 D까지)
        ratings = sorted(filtered_df['신용등급'].dropna().unique().tolist())
        # 색상 그라데이션: 높은 등급(녹색)에서 낮은 등급(빨강)으로
        colors = ['darkgreen', 'green', 'lightgreen', 'blue', 'lightblue', 
                 'orange', 'salmon', 'red', 'darkred', 'black']
        color_map = {r: colors[i % len(colors)] for i, r in enumerate(ratings)}
    elif color_by == '현금흐름등급':
        color_field = '현금흐름등급'
        # 현금흐름등급에 따른 색상
        cf_ratings = sorted(filtered_df['현금흐름등급'].dropna().unique().tolist())
        cf_colors = ['darkgreen', 'green', 'orange', 'red', 'darkred']
        color_map = {}
        for i, r in enumerate(cf_ratings):
            if i < len(cf_colors):
                color_map[r] = cf_colors[i]
            else:
                color_map[r] = 'gray'
    elif color_by == '업종명':
        color_field = '업종명'
        # 업종별 색상 (최대 10개만 구분)
        industries = filtered_df['업종명'].dropna().unique().tolist()
        ind_colors = ['blue', 'red', 'green', 'purple', 'orange', 
                     'darkblue', 'darkgreen', 'darkred', 'cadetblue', 'darkpurple']
        color_map = {ind: ind_colors[i % len(ind_colors)] for i, ind in enumerate(industries)}
    else:  # 기본값
        color_field = None
        color_map = {'default': 'blue'}
    
    # ===== 지도 생성 =====
    if not filtered_df.empty:
        # 로딩 표시
        with st.spinner("지도를 생성하고 있습니다..."):
            # 지도 중심 좌표 계산
            if len(filtered_df) == 1:  # 결과가 하나일 때
                center_lat = filtered_df['latitude'].iloc[0]
                center_lon = filtered_df['longitude'].iloc[0]
                zoom_start = 14
            elif selected_region != '전체' and 'sido' in filtered_df.columns:
                center_lat = filtered_df['latitude'].mean()
                center_lon = filtered_df['longitude'].mean()
                zoom_start = 10 if selected_district == '전체' else 12
            else:  # 전체 지도
                # 한국 중앙 쯤으로 센터 설정
                center_lat, center_lon = 36.0, 127.8
                zoom_start = 7
            
            # 지도 객체 생성
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=zoom_start,
                tiles=None  # 타일 없이 시작
            )
            
            # 선택한 타일 설정
            selected_tile = tile_options[selected_style]
            
            # Google 지도 URL인 경우
            if selected_style.startswith("Google"):
                folium.TileLayer(
                    tiles=selected_tile,
                    attr='Google Maps',
                    name=selected_style,
                ).add_to(m)
            else:
                # 기본 folium 타일
                folium.TileLayer(
                    tiles=selected_tile,
                    name=selected_style,
                ).add_to(m)
            
            # 클러스터링 옵션에 따라 마커 클러스터 설정
            if use_clustering:
                marker_cluster = MarkerCluster(
                    name="기업 클러스터",
                    options={
                        'maxClusterRadius': cluster_radius,
                        'disableClusteringAtZoom': 15,  # 줌 레벨 15 이상에서는 클러스터링 비활성화
                        'spiderfyOnMaxZoom': True,
                        'minClusterSize': min_cluster_size
                    }
                ).add_to(m)
            
            # 마커 추가
            for idx, row in filtered_df.iterrows():
                # 색상 선택
                if color_field and color_field in row and pd.notna(row[color_field]):
                    color = color_map.get(row[color_field], 'gray')
                else:
                    color = color_map.get('default', 'blue')
                
                # 개선된 팝업 스타일 - 컬럼명과 값을 명확하게 구분하고 가독성 향상
                popup_content = """
                <div style="font-family: Arial; width: 320px; max-width: 100%;">
                    <style>
                        .info-table {
                            width: 100%;
                            border-collapse: collapse;
                            margin-bottom: 5px;
                        }
                        .info-table th {
                            text-align: left;
                            padding: 4px 6px;
                            font-weight: bold;
                            color: #2E5984;
                            width: 120px;
                            vertical-align: top;
                            border-bottom: 1px solid #eee;
                            white-space: nowrap;
                        }
                        .info-table td {
                            padding: 4px 6px;
                            vertical-align: top;
                            border-bottom: 1px solid #eee;
                            word-break: break-word;
                        }
                        .company-name {
                            font-weight: bold;
                            font-size: 16px;
                            color: #2E5984;
                            margin: 0;
                            padding: 5px 0;
                            border-bottom: 2px solid #2E5984;
                            margin-bottom: 8px;
                        }
                    </style>
                """
                
                # 기업명을 제목으로 표시
                if '한글업체명' in row and pd.notna(row['한글업체명']):
                    popup_content += f'<div class="company-name">{row["한글업체명"]}</div>'
                
                popup_content += '<table class="info-table">'
                
                # 표시할 필드와 레이블 정의 (요청된 순서대로)
                fields_to_display = [
                    ('기업규모구분', '기업규모구분'),
                    ('업종명', '업종명'),
                    ('업태명', '업태명'),
                    ('주요상품내역', '주요상품내역'),
                    ('산업코드 대분류', '산업코드 대분류'),
                    ('산업코드 세세분류', '산업코드 세세분류'),
                    ('신용등급', '신용등급'),
                    ('현금흐름등급', '현금흐름등급'),
                    ('한글지번주소', '한글지번주소'),
                    ('전화번호', '전화번호'),
                    ('사업자등록번호', '사업자등록번호'),
                    ('한글주소', '한글주소')
                ]
                
                for field, label in fields_to_display:
                    if field in row and pd.notna(row[field]):
                        # 사업자등록번호는 정수형태로 표시 (소수점 제거)
                        if field == '사업자등록번호' and '.' in str(row[field]):
                            value = str(row[field]).split('.')[0]
                        else:
                            value = row[field]
                        
                        popup_content += f"""
                        <tr>
                            <th>{label}</th>
                            <td>{value}</td>
                        </tr>
                        """
                
                popup_content += """
                    </table>
                </div>
                """
                
                # 팝업 생성 - 최대 너비 조정
                popup = folium.Popup(popup_content, max_width=350)
                
                # 마커 생성
                if marker_style == '기본 마커':
                    # 기본 아이콘
                    icon_type = 'building'  # 기본 아이콘
                    
                    # 기업 규모에 따라 다른 아이콘
                    if '기업규모구분' in row and pd.notna(row['기업규모구분']):
                        if row['기업규모구분'] == '대기업':
                            icon_type = 'building'
                        elif row['기업규모구분'] == '중견기업':
                            icon_type = 'industry'
                        elif row['기업규모구분'] == '중소기업':
                            icon_type = 'briefcase'
                        else:
                            icon_type = 'home'
                        
                    marker = folium.Marker(
                        location=[row['latitude'], row['longitude']],
                        popup=popup,
                        tooltip=row.get('한글업체명', '기업명 없음'),
                        icon=folium.Icon(color=color, icon=icon_type, prefix='fa')
                    )
                else:  # 원형 마커
                    marker = folium.CircleMarker(
                        location=[row['latitude'], row['longitude']],
                        radius=6,
                        popup=popup,
                        tooltip=row.get('한글업체명', '기업명 없음'),
                        color=color,
                        fill=True,
                        fill_opacity=0.7,
                        fill_color=color
                    )
                
                # 클러스터링 설정에 따라 마커 추가
                if use_clustering:
                    marker.add_to(marker_cluster)
                else:
                    marker.add_to(m)
            
            # 레전드 제목 및 내용 결정
            if color_field:
                legend_title = {
                    '기업규모구분': '기업 규모',
                    '신용등급': '신용등급',
                    '현금흐름등급': '현금흐름등급',
                    '업종명': '업종'
                }.get(color_field, '분류')
                
                # 레전드 HTML 생성 - 최대 15개 항목만 표시
                legend_html = f"""
                <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border: 1px solid grey; border-radius: 5px; max-height: 300px; overflow-y: auto; max-width: 200px;">
                    <p style="text-align: center; margin-bottom: 5px;"><b>{legend_title}</b></p>
                """
                
                # 필터링된 데이터에 있는 값만 레전드에 표시
                legend_items = []
                for key, color in color_map.items():
                    if key != 'default' and color_field in filtered_df.columns and (filtered_df[color_field] == key).any():
                        legend_items.append((key, color))
                
                # 항목이 너무 많은 경우 줄임
                max_legend_items = 15
                if len(legend_items) > max_legend_items:
                    legend_html += f"<p style='font-size: 10px; color: gray;'>* 표시된 {max_legend_items}개 항목 중 일부</p>"
                    
                for key, color in legend_items[:max_legend_items]:
                    legend_html += f"""
                    <div style="display: flex; align-items: center; margin-bottom: 3px;">
                        <span style="background-color: {color}; width: 15px; height: 15px; display: inline-block; margin-right: 5px; border-radius: 50%;"></span>
                        <span style="font-size: 12px;">{key}</span>
                    </div>
                    """
                
                legend_html += '</div>'
                
                # 레전드를 지도에 추가
                m.get_root().html.add_child(folium.Element(legend_html))
            
            # 레이어 컨트롤 추가
            folium.LayerControl().add_to(m)
        
        # Streamlit에서 folium 지도 표시
        folium_static(m, width=1600, height=800)
    
    else:
        st.warning("검색 조건에 맞는 기업이 없습니다. 검색어나 필터를 조정해주세요.")
    
    # 시각화 설정 및 사용법 안내
    with st.sidebar.expander("📌 사용 가이드"):
        st.markdown("""
        ### 사용 방법
        1. **검색 및 필터링**: 시도/군구, 기업규모, 신용등급, 통합검색으로 기업을 찾아보세요
        2. **검색 버튼 클릭**: 설정한 필터를 적용하여 데이터를 검색합니다
        3. **지도 확인**: 검색 결과가 지도에 마커로 표시됩니다
        4. **마커 클릭**: 클릭하면 기업의 상세 정보를 확인할 수 있습니다
        
        ### 참고사항
        - 가까운 위치의 기업은 클러스터로 그룹화됩니다
        """)

if __name__ == "__main__":
    main()