"""내신 페이스메이커 — 실행: streamlit run app.py
학기 평균을 동일 비중으로 계산하는 학습 계획용 앱. 공식 대입 환산이 아닙니다.
"""
from bisect import bisect_right
from decimal import Decimal, ROUND_HALF_UP
import math
import streamlit as st

SEMESTERS = ['1학년 1학기', '1학년 2학기', '2학년 1학기', '2학년 2학기', '3학년 1학기']
FIVE_MID = (5.0, 22.0, 50.0, 78.0, 95.0)
NINE_MID = (2.0, 7.5, 17.0, 31.5, 50.0, 68.5, 83.0, 92.5, 98.0)
MODES = [
    ('균형 페이스', '남은 학기에 비슷한 목표를 배분합니다.', 'equal'),
    ('차근차근 상승', '시간이 지날수록 목표 등급 숫자가 낮아집니다.', 'rise'),
    ('선공후여유', '초반에 더 좋은 성적을 확보하고, 뒤에는 부담을 줄입니다.', 'front'),
]


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def interpolate(x, xs, ys):
    if x <= xs[0]:
        return float(ys[0])
    if x >= xs[-1]:
        return float(ys[-1])
    j = bisect_right(xs, x) - 1
    return ys[j] + (x - xs[j]) / (xs[j + 1] - xs[j]) * (ys[j + 1] - ys[j])


def to_nine(grade):
    """5등급 평균→가상 중앙 누적비율→9등급 중앙점 선형보간. 추정 석차 아님."""
    if not math.isfinite(grade) or not 1 <= grade <= 5:
        raise ValueError('5등급제 값은 1.00~5.00이어야 합니다.')
    percentile = interpolate(grade, (1, 2, 3, 4, 5), FIVE_MID)
    return interpolate(percentile, NINE_MID, tuple(range(1, 10)))


def plan(total_cents, remaining, mode):
    """0.01 단위로 목표합을 정확히 맞춤. 범위를 넘는 배분은 경계에서 재분배."""
    if remaining < 1 or not 100 * remaining <= total_cents <= 500 * remaining:
        raise ValueError('남은 학기에서 달성할 수 없는 합계입니다.')
    if mode not in {'equal', 'rise', 'front'}:
        raise ValueError('알 수 없는 모드입니다.')
    # 학기 간 기본 차이 0.30등급. 극단 목표에서는 범위 안에서 차이가 축소됩니다.
    offsets = [0.0] * remaining
    if mode != 'equal':
        sign = -1 if mode == 'rise' else 1
        offsets = [sign * (i - (remaining - 1) / 2) * 30 for i in range(remaining)]
    lo, hi = -1000.0, 1500.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if sum(min(500, max(100, mid + o)) for o in offsets) < total_cents:
            lo = mid
        else:
            hi = mid
    raw = [min(500.0, max(100.0, (lo + hi) / 2 + o)) for o in offsets]
    result = [int(math.floor(x + 1e-8)) for x in raw]
    diff = total_cents - sum(result)
    order = sorted(range(remaining), key=lambda i: (raw[i] - result[i], -i), reverse=True)
    for i in order:
        if diff > 0 and result[i] < 500:
            result[i] += 1
            diff -= 1
    if diff != 0:
        raise ArithmeticError('목표 배분 오차가 발생했습니다.')
    if mode == 'rise':
        result.sort(reverse=True)
    else:
        result.sort()
    assert sum(result) == total_cents
    return [x / 100 for x in result]


def main():
    st.set_page_config(page_title='내신 페이스메이커', page_icon='🎯', layout='centered')
    st.markdown('''<style>
    .stApp {background: #f7f9fc;}
    .block-container {max-width: 960px; padding-top: 2rem;}
    h1,h2,h3 {letter-spacing:-0.045em;}
    div.st-key-summary {position:sticky; top:3.65rem; z-index:99;
      background:#12233f; color:#fff; border-radius:18px; padding:18px 24px;
      box-shadow:0 8px 24px #12233f25; margin-bottom:18px;}
    div.st-key-summary p,div.st-key-summary label,
    div.st-key-summary [data-testid="stMetricValue"],
    div.st-key-summary [data-testid="stMetricLabel"] {color:#fff !important;}
    [data-testid="stTabs"] button {font-weight:700;}
    @media(max-width:600px){div.st-key-summary{padding:12px;top:3.5rem;}}
    </style>''', unsafe_allow_html=True)
    st.title('🎯 내신 페이스메이커')
    st.caption('지금의 성적을 확인하고, 3학년 1학기까지 나만의 페이스를 설계하세요.')

    # 결과 표시 위치를 먼저 확보해 입력보다 위에 고정합니다.
    summary = st.container(key='summary')
    st.subheader('01 · 성적 입력')
    st.caption('입력은 모두 5등급제입니다. 성적이 확정된 학기까지만 순서대로 입력하세요.')
    count = st.selectbox('성적이 나온 마지막 학기', range(1, 6),
                         format_func=lambda n: SEMESTERS[n - 1], key='completed')
    grades = []
    cols = st.columns(2)
    for i in range(count):
        with cols[i % 2]:
            grades.append(st.number_input(SEMESTERS[i] + ' 평균등급',
                          min_value=1.0, max_value=5.0, value=3.0,
                          step=0.01, format='%.2f', key=f'grade_{i}'))
    target = st.number_input('최종 목표 평균등급 (5등급제)', min_value=1.0,
                             max_value=5.0, value=2.0, step=0.01, format='%.2f', key='target')
    st.caption('예시 숫자가 입력되어 있습니다. 본인 성적으로 바꾸면 모든 결과가 즉시 갱신됩니다.')
    grade_sum = sum(cents(g) for g in grades)
    current = grade_sum / (100 * count)
    with summary:
        st.markdown('**현재 성적 · 9등급제 참고 환산**')
        a, b = st.columns(2)
        a.metric('9등급제 참고값', f'{to_nine(current):.2f}등급')
        b.metric('입력한 5등급제 평균', f'{current:.2f}등급')
        st.caption(f'{count}/5학기 완료 · 학기 동일 비중 · 공식 환산 아님')

    st.warning('9등급제 값은 누적비율 중앙점 기반의 참고 모델입니다. 평균등급만으로 실제 석차나 '
               '공식 9등급 성적을 알 수 없으며, 대학별 내신 환산점수와 다릅니다.')
    st.subheader('02 · 목표까지의 로드맵')
    st.caption(f'최종 목표: 5등급제 {target:.2f} / 9등급제 참고값 {to_nine(target):.2f} · '
               '등급 숫자가 낮을수록 좋은 성적입니다.')
    remaining = 5 - count
    if remaining == 0:
        if current <= target + 1e-9:
            st.success(f'5학기 최종 평균 {current:.2f}등급으로 목표를 달성했습니다!')
        else:
            st.error(f'5학기가 모두 끝났습니다. 최종 평균은 {current:.2f}등급이며, '
                     f'목표보다 {current - target:.2f}등급 높습니다. 남은 학기가 없어 로드맵을 만들 수 없습니다.')
        return

    best = (grade_sum + 100 * remaining) / 500
    worst = (grade_sum + 500 * remaining) / 500
    needed = cents(target) * 5 - grade_sum
    a, b = st.columns(2)
    a.metric('남은 학기', f'{remaining}학기')
    b.metric('달성 가능한 최선의 최종 평균', f'{best:.2f}',
             help=f'정확한 최선 평균: {best:.3f}. 남은 학기 모두 1.00인 경우입니다.')
    if needed < 100 * remaining:
        st.error(f'현재 목표는 달성 불가능합니다. 남은 학기 모두 1.00이어도 최종 평균은 '
                 f'{best:.3f}등급입니다. 목표는 {math.ceil(best * 100 - 1e-8) / 100:.2f} 이상으로 조정하세요.')
        st.info('범위 밖의 등급을 억지로 제시하지 않습니다. 목표를 바꾸면 3가지 로드맵이 표시됩니다.')
        return
    over_easy = needed > 500 * remaining
    if over_easy:
        st.success(f'현재 목표는 이미 안전권입니다. 남은 학기 모두 5.00이어도 최종 평균은 '
                   f'{worst:.3f}등급으로 목표 이내입니다.')
        st.caption('목표와 정확히 같은 평균은 만들 수 없어, 아래에는 목표보다 좋은 보수적 상한 계획을 표시합니다.')
        needed = 500 * remaining
    else:
        st.info(f'남은 학기에서 필요한 평균: 5등급제 {needed / (100 * remaining):.3f}등급 · '
                f'9등급제 참고값 {to_nine(needed / (100 * remaining)):.2f}')
    if remaining == 1:
        st.caption('남은 학기가 하나라 세 모드의 결과가 같습니다.')
    elif needed in (100 * remaining, 500 * remaining):
        st.caption('등급 범위의 한계에 도달해 세 모드의 결과가 같습니다.')

    tabs = st.tabs([m[0] for m in MODES])
    for tab, (name, description, mode) in zip(tabs, MODES):
        with tab:
            st.markdown(f'### {name}')
            st.write(description)
            values = plan(needed, remaining, mode)
            rows = [{'학기': SEMESTERS[count + i], '5등급제 목표': f'{v:.2f}',
                     '9등급제 참고 환산': f'{to_nine(v):.2f}'} for i, v in enumerate(values)]
            st.table(rows)
            final = (grade_sum + sum(cents(v) for v in values)) / 500
            st.success(f'이 계획의 최종 평균: 5등급제 {final:.3f} / 9등급제 참고값 {to_nine(final):.2f}')
            st.caption('각 학기에서 표의 목표와 같거나 더 좋은 성적을 받으면 최종 목표 이내입니다. '
                       '학기 평균의 소수점 두 자리까지 계획하며, 실제 과목 구성에 따른 구현 가능성은 다를 수 있습니다.')

    with st.expander('계산 방식과 환산 기준 자세히 보기'):
        st.markdown('''**학기 계산**
- 총 5학기: 1학년 1학기부터 3학년 1학기까지. 모든 학기를 같은 비중으로 계산합니다.
- 필요한 남은 성적 합 = 최종 목표 × 5 − 완료한 학기 성적 합.
- 과목별 이수학점·대학별 학년 가중치·성취평가 과목은 별도로 반영하지 않습니다.

**세 모드**
- 균형 페이스: 동일한 목표로 배분하되 0.01 단위에서 차이가 생길 수 있습니다.
- 차근차근 상승: 뒤 학기로 갈수록 목표 숫자가 작아집니다.
- 선공후여유: 앞 학기에 작은 목표 숫자를 배정합니다.
- 기본 학기 간 차이는 0.30입니다. 1.00~5.00 경계에서는 남는 부담을 다른 학기에 재분배합니다.
- 상승 모드는 미래 학기끼리의 추세입니다. 현재 평균보다 첫 목표가 쉬워진다는 보장은 없습니다.

**누적비율 중앙점 참고 모델**
- 5등급 누적 경계: 0, 10, 34, 66, 90, 100%.
- 9등급 누적 경계: 0, 4, 11, 23, 40, 60, 77, 89, 96, 100%.
- 5등급의 구간 중앙점 5, 22, 50, 78, 95%를 등급 1~5와 연결해 선형보간합니다.
- 그 가상 비율을 9등급 구간 중앙점 2, 7.5, 17, 31.5, 50, 68.5, 83, 92.5, 98%에 대응시킵니다.
- 예: 5등급제 1.00 → 참고값 약 1.55, 3.00 → 5.00, 5.00 → 약 8.45.
- 중앙점을 선택했기 때문에 양 끝이 1.00·9.00이 되지 않습니다. 이 보간법 자체는 앱의 가정입니다.
- 학기별 참고값을 평균하는 대신, **5등급제 평균을 먼저 구한 뒤** 환산합니다. 비선형이므로 두 계산은 다릅니다.
- 평균등급은 실제 백분위가 아닙니다. 동일 평균이라도 과목별 성적·석차 분포가 다를 수 있습니다.

비율 참고: [인천광역시 웹진 MOO](https://www.incheon.go.kr/moo/MOO040101/2151854),
[중앙일보 대입제도 확정 보도](https://www.joongang.co.kr/article/25217822).
''')
        st.table([{'5등급제 평균': f'{g:.2f}', '9등급제 참고값': f'{to_nine(g):.2f}'}
                  for g in (1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)])
    st.caption('개인정보·성적을 별도 파일이나 데이터베이스에 저장하지 않습니다. 학습 계획용 참고 도구입니다.')


if __name__ == '__main__':
    main()
