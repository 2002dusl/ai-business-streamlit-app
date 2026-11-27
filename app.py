"""소비·신용 진단 상담 웹앱

AI Business (2026-2) Assignment #2 제출용.
다섯 가지 항목을 차례로 물어보고, 답변을 바탕으로 상환여력과 부채 부담을 정리해 준다.
외부 API 없이 규칙 기반으로 동작하므로 별도 키 없이 실행된다.
"""

import re

import streamlit as st

PASSWORD = "pnumis"

QUESTIONS = [
    {
        "key": "income",
        "name": "월 소득",
        "ask": "먼저 월 소득이 얼마인지 알려 주세요. 세후 실수령액 기준으로 만원 단위 숫자만 적으셔도 됩니다. (예: 280)",
        "unit": "만원",
        "low": 0,
        "high": 5000,
    },
    {
        "key": "repay",
        "name": "월 부채 상환액",
        "ask": "매달 대출 원리금으로 나가는 돈은 얼마인가요? 대출이 없으면 0이라고 적어 주세요.",
        "unit": "만원",
        "low": 0,
        "high": 5000,
        "zero_words": ("없", "안", "제로", "0"),
    },
    {
        "key": "loan",
        "name": "신용대출 잔액",
        "ask": "지금 남아 있는 신용대출·카드론 잔액은 얼마인가요? 없으면 0이라고 적어 주세요.",
        "unit": "만원",
        "low": 0,
        "high": 100000,
        "zero_words": ("없", "안", "제로", "0"),
    },
    {
        "key": "overdue",
        "name": "최근 1년 연체",
        "ask": "최근 1년 동안 카드 대금이나 대출 이자를 기한 안에 못 낸 적이 몇 번 있나요?",
        "unit": "회",
        "low": 0,
        "high": 30,
        "zero_words": ("없", "안", "제로", "0"),
    },
    {
        "key": "usage",
        "name": "카드 사용률",
        "ask": "마지막으로, 신용카드 한도의 몇 퍼센트를 쓰고 계신가요? 감이 안 오시면 대략적인 숫자로 괜찮습니다.",
        "unit": "%",
        "low": 0,
        "high": 100,
        "zero_words": ("없", "안", "제로", "0"),
    },
]

GRADE_TABLE = [
    (80, "A", "안정", "지금 구조를 유지해도 무리가 없습니다."),
    (65, "B", "양호", "큰 문제는 없지만 여유 자금을 조금 더 만들 여지가 있습니다."),
    (50, "C", "주의", "한두 항목이 부담으로 작용하고 있습니다."),
    (35, "D", "관리 필요", "상환 부담이 소득에 비해 높은 편입니다."),
    (0, "E", "위험", "연체나 과다 부채가 겹쳐 있어 우선순위를 정해 줄여야 합니다."),
]


def to_number(text):
    """문장에서 첫 번째 숫자를 뽑는다. '300만원', '3,00' 같은 표기도 처리."""
    cleaned = text.replace(",", "").replace(" ", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def read_answer(question, text):
    """답변 문장을 숫자로 바꾸고, 질문 범위를 벗어나면 None을 돌려준다."""
    if any(word in text for word in question.get("zero_words", ())) and not re.search(r"\d", text):
        return 0.0
    value = to_number(text)
    if value is None:
        return None
    if value < question["low"] or value > question["high"]:
        return None
    return value


def dti_point(dti):
    if dti <= 20:
        return 30, "여유"
    if dti <= 30:
        return 24, "적정"
    if dti <= 40:
        return 16, "다소 높음"
    if dti <= 50:
        return 9, "높음"
    return 3, "매우 높음"


def leverage_point(ratio):
    if ratio <= 0.3:
        return 20, "낮음"
    if ratio <= 0.6:
        return 16, "보통"
    if ratio <= 1.0:
        return 10, "높음"
    return 4, "매우 높음"


def overdue_point(count):
    if count == 0:
        return 30, "없음"
    if count == 1:
        return 20, "가벼움"
    if count == 2:
        return 12, "주의"
    return 4, "심각"


def usage_point(usage):
    if usage <= 30:
        return 20, "안정"
    if usage <= 50:
        return 15, "보통"
    if usage <= 70:
        return 9, "높음"
    return 3, "매우 높음"


def diagnose(profile):
    """다섯 항목을 100점 만점으로 환산하고 항목별 코멘트를 만든다."""
    income = max(profile["income"], 1)
    repay = profile["repay"]
    loan = profile["loan"]
    overdue = int(profile["overdue"])
    usage = profile["usage"]

    dti = repay / income * 100
    ratio = loan / (income * 12)

    rows = []
    total = 0

    point, label = dti_point(dti)
    total += point
    rows.append({
        "name": "부채상환비율(DTI)",
        "value": f"{dti:.1f}%",
        "label": label,
        "point": point,
        "max": 30,
        "comment": "월 소득 중 대출 상환에 들어가는 비중입니다. 30% 아래면 은행 심사에서도 무리한 수준으로 보지 않습니다."
        if dti <= 30
        else "소득에 비해 매달 나가는 상환액이 큽니다. 만기 연장이나 금리 낮은 상품으로 바꾸는 것을 먼저 검토해 볼 만합니다.",
    })

    point, label = leverage_point(ratio)
    total += point
    rows.append({
        "name": "연소득 대비 대출잔액",
        "value": f"{ratio:.2f}배",
        "label": label,
        "point": point,
        "max": 20,
        "comment": "1년치 소득보다 적은 수준이라 부채 규모 자체는 관리 가능한 범위입니다."
        if ratio <= 1.0
        else "1년 소득을 넘는 잔액이 남아 있습니다. 추가 대출보다는 원금을 줄이는 쪽이 낫습니다.",
    })

    point, label = overdue_point(overdue)
    total += point
    rows.append({
        "name": "최근 1년 연체",
        "value": f"{overdue}회",
        "label": label,
        "point": point,
        "max": 30,
        "comment": "연체가 없어 신용 이력에서 감점 요인이 없습니다."
        if overdue == 0
        else "연체 기록은 한 번만 생겨도 신용평점에 오래 남습니다. 자동이체를 걸어 두는 편이 안전합니다.",
    })

    point, label = usage_point(usage)
    total += point
    rows.append({
        "name": "카드 사용률",
        "value": f"{usage:.0f}%",
        "label": label,
        "point": point,
        "max": 20,
        "comment": "한도의 30% 안쪽에서 쓰고 있어 신용점수에 불리하지 않습니다."
        if usage <= 30
        else "한도의 절반을 넘겨 쓰고 있습니다. 결제일을 나누거나 한도를 조정하면 사용률을 낮출 수 있습니다.",
    })

    grade, grade_name, summary = "E", "위험", ""
    for cut, code, name, text in GRADE_TABLE:
        if total >= cut:
            grade, grade_name, summary = code, name, text
            break

    weak = sorted(rows, key=lambda row: row["point"] / row["max"])[:2]
    actions = build_actions(weak[0]["name"], weak[1]["name"], profile)

    return {
        "score": total,
        "grade": grade,
        "grade_name": grade_name,
        "summary": summary,
        "rows": rows,
        "actions": actions,
        "dti": dti,
        "ratio": ratio,
    }


def build_actions(first, second, profile):
    """가장 약한 두 항목에 맞춰 실행 순서를 정한다."""
    first_actions = {
        "부채상환비율(DTI)": "월 상환액을 소득의 30% 이내로 낮추는 것을 목표로 잡으세요. 금리가 높은 대출부터 갈아타거나 만기를 늘리는 방법이 있습니다.",
        "연소득 대비 대출잔액": "연말 상여나 남는 현금이 생기면 중도상환수수료가 없는 대출부터 원금을 줄이는 편이 좋습니다.",
        "최근 1년 연체": "카드 대금과 대출 이자의 결제일을 확인하고 자동이체를 걸어 두세요. 잔액 부족 알림도 함께 켜 두면 연체를 막을 수 있습니다.",
        "카드 사용률": "한도의 30% 이내로 쓰는 습관을 먼저 만드세요. 결제일을 분산하거나 체크카드를 함께 쓰는 방법이 쉽습니다.",
    }
    second_actions = {
        "부채상환비율(DTI)": "상환액을 줄이기 어렵다면 소득을 늘리는 쪽도 함께 봐야 합니다. 고정 지출을 먼저 정리해 보세요.",
        "연소득 대비 대출잔액": "새 대출은 잔액을 늘리므로, 필요한 지출인지 한 번 더 확인하세요.",
        "최근 1년 연체": "연체가 반복되면 신용점수가 떨어지므로, 결제일 전에 잔액을 확인하는 습관을 권합니다.",
        "카드 사용률": "사용률이 높으면 신용점수 계산에서 불리합니다. 한도 상향보다 사용액을 줄이는 쪽이 효과적입니다.",
    }
    return [first_actions[first], second_actions[second]]


def format_result(result):
    lines = [
        f"**진단 결과 — 종합 {result['score']}점 ({result['grade']} · {result['grade_name']})**",
        "",
        "| 항목 | 고객 값 | 평가 | 배점 |",
        "|---|---|---|---|",
    ]
    for row in result["rows"]:
        lines.append(f"| {row['name']} | {row['value']} | {row['label']} | {row['point']}/{row['max']} |")
    lines += ["", result["summary"], "", "**먼저 해 볼 일**", ""]
    for index, action in enumerate(result["actions"], start=1):
        lines.append(f"{index}. {action}")
    lines += ["", "궁금한 점은 이어서 물어보셔도 됩니다. (예: \"DTI가 뭐예요?\", \"한도 조정하면 어떻게 돼요?\", \"다시 진단\")"]
    return "\n".join(lines)


def josa_ro(word):
    """받침 유무에 따라 '으로'와 '로'를 고른다."""
    last = word[-1]
    if "가" <= last <= "힣":
        code = ord(last) - ord("가")
        has_batchim = code % 28 != 0
        if has_batchim and last != "ㄹ":
            return "으로"
    return "로"


def answer_question(text, profile, result):
    """진단 이후의 자유 질문에 규칙으로 답한다."""
    lowered = text.replace(" ", "").lower()

    if any(word in lowered for word in ("다시", "처음", "새로", "리셋", "초기화")):
        reset_state()
        return START_MESSAGE

    if any(word in lowered for word in ("dti", "부채상환비율", "상환비율")):
        return (
            f"DTI는 Debt To Income, 즉 소득 대비 대출 상환액 비율입니다. "
            f"고객님은 월 소득 {profile['income']:.0f}만원 중 {profile['repay']:.0f}만원을 상환에 쓰고 있어 {result['dti']:.1f}%로 계산됩니다. "
            "은행에서는 보통 40% 이하를 기준으로 보지만, 30% 아래면 여유가 있는 편으로 봅니다."
        )

    if any(word in lowered for word in ("신용점수", "신용등급", "점수", "등급")):
        return (
            "여기서 나오는 점수는 상담용으로 다섯 항목을 100점 만점에 배점한 값이고, NICE나 KCB의 실제 신용점수와는 다릅니다. "
            "실제 점수는 카드 사용 이력과 대출 상환 기록이 누적되어 계산되므로, 조회는 각 사이트에서 직접 하셔야 합니다."
        )

    if any(word in lowered for word in ("연체", "밀렸", "못냈")):
        if profile["overdue"] == 0:
            return "최근 1년 연체가 없어 이 항목에서는 감점이 없습니다. 결제일 자동이체만 유지하면 됩니다."
        return (
            f"최근 1년 연체가 {profile['overdue']:.0f}회 있습니다. 연체는 갚은 뒤에도 일정 기간 기록이 남기 때문에, "
            "지금부터 결제일을 지키는 것이 가장 중요합니다. 카드사 앱에서 자동이체와 잔액 알림을 함께 설정해 두세요."
        )

    if any(word in lowered for word in ("한도", "카드", "사용률")):
        return (
            f"카드 사용률은 {profile['usage']:.0f}%입니다. 한도의 30% 안쪽이면 신용점수에 불리하지 않고, "
            "50%를 넘으면 부채로 인식되는 비중이 커집니다. 한도를 올리기보다 사용액을 줄이는 쪽이 점수에 유리합니다."
        )

    if any(word in lowered for word in ("대출", "승인", "가능", "심사")):
        return (
            "심사 결과는 여기서 단정할 수 없습니다. 은행은 소득 증빙, 기존 대출, 연체 이력, 신용점수를 함께 보고, "
            "같은 조건이라도 상품과 시점에 따라 기준이 다릅니다. 상담 내용은 준비 상태를 점검하는 용도로 봐 주세요."
        )

    if "소득" in lowered and to_number(lowered) is not None:
        new_income = to_number(lowered)
        if 0 < new_income <= 5000:
            changed = dict(profile)
            changed["income"] = new_income
            new_result = diagnose(changed)
            return (
                f"월 소득을 {new_income:.0f}만원으로 바꿔 다시 계산해 봤습니다. "
                f"종합 {new_result['score']}점({new_result['grade']})으로, 이전 {result['score']}점에서 "
                f"{new_result['score'] - result['score']:+d}점 변합니다. DTI는 {new_result['dti']:.1f}%입니다."
            )

    if any(word in lowered for word in ("저축", "모으", "비상금")):
        return (
            f"현재 상환액을 빼면 월 {profile['income'] - profile['repay']:.0f}만원이 남습니다. "
            "이 중 10~20%를 비상금으로 따로 떼어 두면, 갑작스러운 지출로 연체가 생기는 일을 줄일 수 있습니다."
        )

    return (
        "그 부분은 제가 정리해 둔 범위 밖이라 정확히 답하기 어렵습니다. "
        "DTI, 연체, 카드 사용률, 대출 심사, 저축 계획 중에서 궁금한 것을 말씀해 주시면 다시 설명해 드릴게요."
    )


START_MESSAGE = (
    "안녕하세요. 소비·신용 진단 상담을 시작하겠습니다.\n\n"
    "월 소득, 부채 상환액, 대출 잔액, 최근 연체, 카드 사용률 다섯 가지만 여쭤보고 "
    "현재 상태를 정리해 드립니다. 입력하신 값은 저장하지 않습니다.\n\n"
    + QUESTIONS[0]["ask"]
)


def reset_state():
    st.session_state.messages = [{"role": "assistant", "content": START_MESSAGE}]
    st.session_state.profile = {}
    st.session_state.step = 0
    st.session_state.result = None


def handle_message(text):
    step = st.session_state.step
    profile = st.session_state.profile

    if step is not None and step < len(QUESTIONS):
        question = QUESTIONS[step]
        value = read_answer(question, text)
        if value is None:
            return (
                f"숫자로 다시 말씀해 주시겠어요? {question['name']}은(는) {question['unit']} 단위로, "
                f"0에서 {question['high']} 사이 값이면 됩니다."
            )
        profile[question["key"]] = value
        st.session_state.step = step + 1

        if st.session_state.step < len(QUESTIONS):
            answer = f"{value:,.0f}{question['unit']}"
            return f"네, {question['name']} {answer}{josa_ro(answer)} 확인했습니다.\n\n{QUESTIONS[st.session_state.step]['ask']}"

        st.session_state.step = None
        result = diagnose(profile)
        st.session_state.result = result
        return format_result(result)

    result = st.session_state.result
    if result is None:
        reset_state()
        return START_MESSAGE
    return answer_question(text, profile, result)


def render_login():
    st.markdown(
        """
        <style>
        .login-card { background: #FFFFFF; border: 1px solid #DDE5EC; border-radius: 10px; padding: 30px 30px 26px 30px; }
        .login-kicker { font-size: 11px; letter-spacing: 1.6px; color: #1F8A70; font-weight: 700; }
        .login-title { font-size: 22px; font-weight: 700; color: #10243E; margin-top: 8px; }
        .login-sub { font-size: 13px; color: #5C6B7A; margin-top: 8px; line-height: 1.65; }
        .login-foot { text-align: center; font-size: 11.5px; color: #8FA0B0; margin-top: 18px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:13vh"></div>', unsafe_allow_html=True)
    _, middle, _ = st.columns([1, 1.6, 1])
    with middle:
        st.markdown(
            """
            <div class="login-card">
              <div class="login-kicker">AI BUSINESS · ASSIGNMENT #2</div>
              <div class="login-title">소비·신용 진단 상담</div>
              <div class="login-sub">수업 제출용 웹앱입니다. 안내받은 접속 비밀번호를 입력해 주세요.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        password = st.text_input(
            "접속 비밀번호", type="password", label_visibility="collapsed", placeholder="접속 비밀번호"
        )
        if st.button("들어가기", use_container_width=True):
            if password == PASSWORD:
                st.session_state.auth = True
                reset_state()
                st.rerun()
            else:
                st.error("비밀번호가 맞지 않습니다.")
        st.markdown(
            '<div class="login-foot">AI Business (2026-2) · 경영학과 최승연 (202143316)</div>',
            unsafe_allow_html=True,
        )


def main():
    st.set_page_config(page_title="소비·신용 진단 상담", page_icon="", layout="centered")

    st.markdown(
        """
        <style>
        .stApp { background: #F7F9FB; }
        .block-container { padding-top: 2.2rem; max-width: 880px; }
        .app-header { background: #10243E; border-radius: 10px; padding: 20px 24px; margin-bottom: 6px; }
        .app-kicker { color: #1F8A70; font-size: 10.5px; letter-spacing: 1.6px; font-weight: 700; }
        .app-title { color: #FFFFFF; font-size: 22px; font-weight: 700; margin-top: 6px; }
        .app-sub { color: #A9BDD1; font-size: 12.5px; margin-top: 5px; }
        .app-foot { color: #5C6B7A; font-size: 11.5px; margin-top: 26px; padding-top: 12px; border-top: 1px solid #DDE5EC; }
        .stButton > button { background: #10243E; color: #FFFFFF; border: 1px solid #10243E; font-weight: 600; }
        .stButton > button:hover { background: #1F8A70; border-color: #1F8A70; color: #FFFFFF; }
        .stButton > button:focus { background: #10243E; color: #FFFFFF; border-color: #10243E; box-shadow: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.get("auth"):
        render_login()
        st.stop()

    st.markdown(
        """
        <div class="app-header">
          <div class="app-kicker">PERSONAL FINANCE COUNSELING</div>
          <div class="app-title">소비·신용 진단 상담</div>
          <div class="app-sub">다섯 가지만 확인하고 현재 상환 구조를 정리해 드립니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("**진단 기준**")
        st.caption("다섯 항목을 100점으로 환산합니다.")
        st.markdown(
            "- 부채상환비율(DTI) 30점\n"
            "- 연소득 대비 대출잔액 20점\n"
            "- 최근 1년 연체 30점\n"
            "- 카드 사용률 20점"
        )
        st.divider()
        st.markdown("**등급 구간**")
        st.markdown(
            "- 80점 이상 A 안정\n"
            "- 65~79점 B 양호\n"
            "- 50~64점 C 주의\n"
            "- 35~49점 D 관리 필요\n"
            "- 35점 미만 E 위험"
        )
        st.divider()
        if st.button("상담 처음부터", use_container_width=True):
            reset_state()
            st.rerun()

    if "messages" not in st.session_state:
        reset_state()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("답변을 입력하세요")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        reply = handle_message(user_input)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.markdown(
        '<div class="app-foot">AI Business (2026-2) 웹응용시스템 실습 · 입력한 값은 서버에 저장하지 않습니다.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
