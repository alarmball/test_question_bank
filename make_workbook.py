from pathlib import Path
from html import escape
from math import sin, pi

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, CondPageBreak,
    KeepTogether, Table, TableStyle, Flowable,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output' / 'pdf' / '졸업시험_핵심문제집.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Malgun', r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('MalgunBold', r'C:\Windows\Fonts\malgunbd.ttf'))
pdfmetrics.registerFontFamily('Malgun', normal='Malgun', bold='MalgunBold')

NAVY = colors.HexColor('#162B46')
BLUE = colors.HexColor('#286AA6')
PALE = colors.HexColor('#EAF2F9')
INK = colors.HexColor('#243142')
MUTED = colors.HexColor('#607082')

S = {
    'cover_kicker': ParagraphStyle('cover_kicker', fontName='MalgunBold', fontSize=11, leading=17, textColor=BLUE),
    'cover_title': ParagraphStyle('cover_title', fontName='MalgunBold', fontSize=31, leading=43, textColor=NAVY),
    'cover_sub': ParagraphStyle('cover_sub', fontName='Malgun', fontSize=14, leading=23, textColor=MUTED),
    'h1': ParagraphStyle('h1', fontName='MalgunBold', fontSize=17, leading=26, textColor=NAVY, spaceBefore=5*mm, spaceAfter=4*mm),
    'h2': ParagraphStyle('h2', fontName='MalgunBold', fontSize=12.5, leading=19, textColor=BLUE, spaceBefore=4*mm, spaceAfter=2*mm),
    'body': ParagraphStyle('body', fontName='Malgun', fontSize=9.4, leading=15.8, textColor=INK, spaceAfter=2.2*mm),
    'small': ParagraphStyle('small', fontName='Malgun', fontSize=8.3, leading=13.2, textColor=MUTED, spaceAfter=1.8*mm),
    'question': ParagraphStyle('question', fontName='MalgunBold', fontSize=10.7, leading=18, textColor=NAVY, spaceAfter=3*mm),
    'answer': ParagraphStyle('answer', fontName='Malgun', fontSize=9.1, leading=15.2, textColor=INK, leftIndent=4*mm, firstLineIndent=-4*mm, spaceAfter=2.4*mm),
    'table': ParagraphStyle('table', fontName='Malgun', fontSize=8.5, leading=13.5, textColor=INK),
}

def P(s, sty='body'):
    return Paragraph(s, S[sty])

def E(s):
    return escape(s).replace('\n', '<br/>')

class Rule(Flowable):
    def __init__(self, color=BLUE, width=170*mm):
        super().__init__(); self.color=color; self.width=width; self.height=3*mm
    def draw(self):
        self.canv.setStrokeColor(self.color); self.canv.setLineWidth(1.2)
        self.canv.line(0, self.height/2, self.width, self.height/2)

class SignalDiagram(Flowable):
    def __init__(self):
        super().__init__(); self.width=165*mm; self.height=53*mm
    def draw(self):
        c=self.canv; w=self.width; h=self.height
        c.setFont('Malgun', 8)
        labels=['① 연속 신호','② 표본화','③ 양자화']
        colw=w/3
        for j,lab in enumerate(labels):
            x0=j*colw
            c.setFillColor(NAVY); c.drawString(x0+3*mm,h-5*mm,lab)
            c.setStrokeColor(colors.HexColor('#BECAD5')); c.setLineWidth(.5)
            c.line(x0+3*mm,8*mm,x0+colw-3*mm,8*mm)
            c.line(x0+3*mm,8*mm,x0+3*mm,h-10*mm)
            c.setStrokeColor(BLUE); c.setLineWidth(1.2)
            if j==0:
                p=c.beginPath()
                for i in range(101):
                    x=x0+3*mm+(colw-6*mm)*i/100
                    y=23*mm+11*mm*sin(2*pi*i/100)
                    (p.moveTo if i==0 else p.lineTo)(x,y)
                c.drawPath(p)
            else:
                for i in range(9):
                    x=x0+3*mm+(colw-6*mm)*i/8
                    y=23*mm+11*mm*sin(2*pi*i/8)
                    if j==2: y=round(y/(5*mm))*5*mm
                    c.line(x,8*mm,x,y)
                    c.setFillColor(BLUE); c.circle(x,y,1.25*mm,stroke=0,fill=1)
            if j<2:
                c.setStrokeColor(colors.HexColor('#D8E1EA'))
                c.line(x0+colw,2*mm,x0+colw,h-2*mm)

class Book(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4, leftMargin=21*mm, rightMargin=20*mm,
                         topMargin=21*mm, bottomMargin=21*mm, title='졸업시험 핵심 문제집',
                         author='학습용 편집본')
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='main', frames=[frame], onPage=self.decorate))
    def decorate(self,c,doc):
        n=doc.page; c.saveState()
        if n>1:
            c.setStrokeColor(colors.HexColor('#D5DFE9')); c.setLineWidth(.6)
            c.line(21*mm, A4[1]-16*mm, A4[0]-20*mm, A4[1]-16*mm)
            c.setFont('MalgunBold',8); c.setFillColor(MUTED)
            c.drawString(21*mm,A4[1]-13*mm,'졸업시험 핵심 문제집')
            c.setFont('Malgun',8)
            c.drawRightString(A4[0]-20*mm,13*mm,str(n))
        c.restoreState()

story=[]
def add(*items): story.extend(items)
def section(title): add(P(title,'h1'),Rule())
def item(label, text): add(P(f'<b>{label}</b> {E(text)}'))

add(Spacer(1,40*mm),P('12개 원문 주제 · 24개 학습 문항','cover_kicker'),Spacer(1,6*mm),
    P('졸업시험<br/>핵심 문제집','cover_title'),Spacer(1,8*mm),Rule(),Spacer(1,8*mm),
    P('컴퓨터 보안 · 문화콘텐츠 · 멀티미디어 · 디지털 연산 · 파이썬','cover_sub'),
    Spacer(1,23*mm),
    P('원문 5쪽을 분석해 문항을 다시 구성하고, 연습 문제와 모범답안을 덧붙인 학습용 편집본입니다.','body'),
    P('2026년 10월 30일 제작  |  원문 출처: 「졸업시험 드가자.pdf」, 1~5쪽','small'),PageBreak())

section('이 책의 사용법')
add(P('원문에 나온 12개 주제를 4개 영역으로 묶었습니다. 각 주제마다 핵심 문항 1개와 응용 문항 1개가 있습니다. 먼저 답을 가리고 작성한 다음, 뒤의 모범답안에서 핵심어와 논리 순서를 확인하세요.'),
    P('권장 답안 길이: 정의형 3~5문장, 과정 설명형 5~8문장. 필요한 경우 표·간단한 그림을 함께 사용합니다.'),
    P('원문 점검 사항','h2'),
    P('① 5번은 도식으로 제시된 기획 절차를 문장형 답안으로 정리했습니다. ② 8번은 원문에 예시만 있어 학습 가능한 개념·활용·유의점을 보완했습니다. ③ 9번의 시장 수치는 기준과 출처가 확인되지 않아 최신 통계로 단정하지 않고, 자료 비판형 문항으로 바꿨습니다. ④ 12번의 참조 계수와 순환 수거 설명은 CPython 구현을 기준으로 다듬었습니다.'),
    P('목차','h2'))
toc=[('I. 보안','1~2번 / 원문 1~2쪽'),('II. 콘텐츠 산업·기획','3~5번 / 원문 2쪽'),('III. 신호·연산','6~7번 / 원문 3~4쪽'),('IV. 스마트 기술·산업 자료','8~9번 / 원문 4쪽'),('V. 파이썬 실행 구조','10~12번 / 원문 4~5쪽')]
t=Table([[P(a,'table'),P(b,'table')] for a,b in toc],colWidths=[62*mm,103*mm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.white),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#DDE5ED')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),3*mm),('BOTTOMPADDING',(0,0),(-1,-1),2.5*mm),('TOPPADDING',(0,0),(-1,-1),2.5*mm)]))
add(t,PageBreak())

units=[
('I. 보안',[
 ('01','보안 영역','원문 1쪽','컴퓨터(정보) 보안 영역 다섯 가지를 제시하고, 각 영역의 보호 대상과 대표적인 위험 또는 대응 방법을 설명하시오.','한 조직의 웹 서비스에 XSS, 계정 탈취, DDoS, 취약한 소스 코드, 분실된 업무용 휴대전화가 동시에 발견되었다. 각 문제를 주된 보안 영역에 연결하시오.'),
 ('02','보안 직무','원문 1~2쪽','보안 제품 개발자, 침해사고 대응 전문가, 악성코드 분석 전문가, 디지털 포렌식 전문가, 보안 컨설턴트의 역할을 비교하시오.','랜섬웨어 감염 신고가 들어왔다. 초기 대응, 악성코드 분석, 증거 보존·분석, 재발 방지 설계에 적합한 직무를 각각 배치하고 협업 흐름을 쓰시오.'),
]),
('II. 콘텐츠 산업과 기획',[
 ('03','문화콘텐츠와 산업','원문 2쪽','문화콘텐츠와 문화콘텐츠산업을 각각 정의하고, 이 산업의 특성 세 가지를 설명하시오.','하나의 웹툰이 드라마, 게임, 캐릭터 상품으로 확장되었다. OSMU 관점에서 기대 효과와 주의할 점을 각각 두 가지 쓰시오.'),
 ('04','콘텐츠 산업 분야','원문 2쪽','콘텐츠 산업에 속하는 분야를 열 가지 이상 쓰고, 서로 겹칠 수 있는 분야 두 쌍을 예로 드시오.','행사장에서 게임 IP의 캐릭터 전시, 애니메이션 상영, 굿즈 판매가 동시에 이루어진다. 관련 산업 분야를 네 가지 이상 분류하시오.'),
 ('05','디지털 콘텐츠 기획 절차','원문 2쪽','요구 분석부터 사용성 테스트까지 디지털 콘텐츠 기획의 일반적인 단계를 순서대로 제시하고 각 단계의 산출물을 설명하시오.','교육용 앱의 사용성 테스트에서 학습자가 메뉴를 찾기 어렵다는 결과가 나왔다. 어느 단계로 되돌아가 무엇을 수정하고, 어떻게 다시 검증할지 설명하시오.'),
]),
('III. 멀티미디어와 디지털 연산',[
 ('06','아날로그-디지털 변환','원문 3쪽','아날로그 신호가 디지털 신호가 되는 과정을 표본화, 양자화, 부호화 순서로 설명하고, 표본화 주파수와 양자화 비트 수의 의미를 쓰시오.','최고 주파수가 4 kHz인 신호를 표본화한다. 이론상 필요한 최소 표본화 주파수는 얼마인가? 8비트와 12비트 양자화의 단계 수를 비교하시오.'),
 ('07','2의 보수와 뺄셈','원문 3~4쪽','8비트 2의 보수를 이용하여 5-7을 계산하고, 결과를 10진수로 해석하시오.','8비트 연산으로 13-6을 계산하시오. 피감수, 감수의 2의 보수, 합, 결과 해석을 순서대로 쓰시오.'),
]),
('IV. 스마트 기술과 산업 자료',[
 ('08','AI·빅데이터 융합','원문 4쪽','AI와 빅데이터가 활용되는 스마트 기술을 다섯 가지 제시하고 각 기술의 입력 데이터와 활용 사례를 간단히 쓰시오.','스마트 공장을 기획한다. 센서, 데이터 수집, 예측 모델, 현장 조치가 이어지는 흐름을 설계하고 오탐지·개인정보 또는 안전 문제를 한 가지 이상 설명하시오.'),
 ('09','게임 산업 현황 분석','원문 4쪽','한국 게임 산업의 시장 규모와 수출 비중을 설명하는 답안을 작성할 때 확인해야 할 통계의 기준, 출처, 시점을 쓰고, 산업의 문제와 개선 방향을 논하시오.','“게임 수출 비중이 59%이고, 2024년에 3.9% 성장했다”라는 문장을 보고 그대로 인용하기 전에 점검할 네 가지 질문을 쓰시오.'),
]),
('V. 파이썬 실행 구조',[
 ('10','모든 것은 객체','원문 4쪽','파이썬에서 수, 문자열, 함수, 클래스, 모듈이 객체라는 말의 뜻을 설명하고, 실행 중 이름의 바인딩을 바꿀 수 있다는 점을 동적 바인딩과 연결하시오.','함수를 변수에 대입한 뒤 다른 함수로 다시 바인딩하면 호출 결과가 달라진다. 짧은 예제를 만들고 이름·객체·참조의 관계를 설명하시오.'),
 ('11','import와 모듈 캐시','원문 5쪽','파이썬에서 import 시 모듈 탐색, 객체 생성·실행, sys.modules 등록, 이름 바인딩의 관계를 설명하시오.','순환 import 중 한 모듈의 속성에 접근할 때 오류가 발생할 수 있는 이유와, 의존성을 줄이는 개선책 두 가지를 제시하시오.'),
 ('12','참조 계수와 순환 수거','원문 5쪽','CPython의 참조 계수와 순환 참조 수거가 각각 필요한 이유를 설명하고, 도달 가능한 객체와 접근 불가능한 순환 객체를 구분하시오.','두 객체가 서로 참조한다. 외부 참조를 모두 제거한 뒤에도 참조 계수만으로는 즉시 회수되지 않을 수 있는 이유와 가비지 컬렉터의 역할을 설명하시오.'),
])]

section('Part 1. 실전 문제')
add(P('각 번호의 A는 원문을 토대로 다시 쓴 핵심 문항, B는 적용·검증을 위한 새 연습 문항입니다. 답안은 Part 2에 있습니다.','small'))
for u, qs in units:
    add(CondPageBreak(48*mm),P(u,'h1'))
    for num,title,src,a,b in qs:
        add(KeepTogether([P(f'{num}  {E(title)}','h2'),P(f'출처: {src}','small'),
            P('A. '+E(a),'question'),P('B. '+E(b),'question'),Spacer(1,5*mm)]))
    add(Spacer(1,2*mm))
add(P('학습 점검표','h2'),P('각 문항을 채점하세요. 2점: 핵심어와 설명이 정확함 / 1점: 일부만 설명함 / 0점: 다시 학습 필요. A와 B를 합한 총점은 48점입니다.','small'))
check=Table([[P(f'{i:02d}  {title}','table'),P('A ____ / 2     B ____ / 2','table')]
             for i,(_,qs) in enumerate([(None,[q]) for group in units for q in group[1]],1)
             for _,title,_,_,_ in qs],colWidths=[89*mm,76*mm])
check.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#DDE5ED')),
                           ('TOPPADDING',(0,0),(-1,-1),2.3*mm),('BOTTOMPADDING',(0,0),(-1,-1),2.3*mm),
                           ('LEFTPADDING',(0,0),(-1,-1),2*mm)]))
add(check,PageBreak())

section('Part 2. 모범답안과 해설')
answers=[
('01','시스템 보안은 운영체제·계정·권한·로그·패치 등 시스템 자체를 보호한다. 네트워크 보안은 통신 경로와 서비스를 DDoS, 스푸핑, 세션 탈취 등에서 보호한다. 웹 보안은 웹 서비스의 입력과 요청을 다루며 XSS·CSRF 등을 예방한다. 코드 보안은 소스 코드와 구현 과정의 결함을 찾고 수정한다. 모바일 보안은 휴대전화와 앱·데이터를 분실, 악성 앱, 불안전한 연결 등에서 보호한다. 영역은 겹칠 수 있다.','XSS→웹, 계정 탈취→시스템(인증), DDoS→네트워크, 취약한 소스 코드→코드, 분실 휴대전화→모바일 보안. 실제 대응에서는 여러 영역을 함께 점검한다.'),
('02','제품 개발자는 방화벽·탐지 도구 등 보안 소프트웨어를 만든다. 침해사고 대응 전문가는 사고 범위 파악, 격리, 복구, 재발 방지를 조정한다. 악성코드 분석 전문가는 실행 행위와 감염 경로를 분석한다. 디지털 포렌식 전문가는 증거를 보존하고 사건의 경과를 재구성한다. 컨설턴트는 위험을 평가하고 정책·기술 대책을 설계한다.','대응 전문가가 신고를 접수해 시스템을 격리하고, 포렌식 전문가가 원본 증거와 로그를 보존한다. 악성코드 분석 전문가가 유포·암호화 동작을 분석한다. 대응팀이 복구하고, 컨설턴트가 취약점과 운영 절차를 개선한다. 각 단계의 증거 인계와 기록이 중요하다.'),
('03','문화콘텐츠는 문화적 요소와 창의성을 바탕으로 경제적 가치를 만드는 상품·서비스다. 문화콘텐츠산업은 이를 기획·제작·유통·소비하는 관련 산업이다. 특성으로 초기 제작비는 크지만 추가 복제·유통 비용은 상대적으로 낮을 수 있고, 흥행 성과의 불확실성이 크며, 하나의 원천 IP를 여러 매체로 확장하는 OSMU가 가능하다. 해외 유통과 파급 효과도 있다.','기대 효과: 같은 IP의 인지도와 수익 경로 확대, 매체 간 홍보 효과. 주의점: 원작의 핵심 설정·품질 유지, 저작권·계약 및 매체별 이용자 특성 검토.'),
('04','예: 게임, 모바일 콘텐츠, 애니메이션, 영화, 출판, 음악, 방송, 캐릭터, 만화, 이러닝, 축제·이벤트, 디지털 박물관, 테마파크. 모바일 게임은 게임과 모바일 콘텐츠에, 웹툰 원작 애니메이션은 만화와 애니메이션에 함께 걸칠 수 있다.','게임, 캐릭터, 애니메이션, 축제·이벤트를 우선 분류할 수 있다. 굿즈의 출판물이나 모바일 홍보물이 있다면 출판·모바일 콘텐츠도 관련된다.'),
('05','① 요구 분석·사용자 정의: 목표, 요구사항, 대상 이용자. ② 환경 분석: 시장·경쟁·기술·제약 조사. ③ 디자인 방향 설정: 콘셉트, 차별화 전략, 톤과 매너. ④ 시나리오·정보 구조 설계: 이용 흐름과 화면 구조. ⑤ 스토리보드 제작: 와이어프레임과 주요 화면·상호작용. ⑥ 프로토타이핑·사용성 테스트: 실제 이용 과제를 수행하게 하여 문제를 찾고 수정한다. 반복 개선이 가능하다.','문제의 원인이 메뉴 명칭·위치인지 확인하고, 요구사항과 정보 구조를 재검토한다. 화면 구조와 스토리보드를 수정해 프로토타입을 만든 뒤 동일한 찾기 과제로 성공률, 소요 시간, 오류·의견을 비교한다.'),
('06','표본화는 연속 신호를 일정 간격의 시점에서 측정한다. 양자화는 측정된 진폭을 유한한 단계 중 하나로 근사하며 오차가 생긴다. 부호화는 그 단계 값을 비트열로 나타낸다. 신호의 최고 주파수가 f라면 이상적인 조건에서 표본화 주파수는 2f보다 커야 원 신호 복원이 가능하다. 양자화 n비트는 2^n개의 단계다.','최고 4 kHz 신호의 이론적 경계는 8 kHz이며, 실제 설계에서는 경계보다 높은 주파수와 아날로그 저역 통과 필터를 사용한다. 8비트는 256단계, 12비트는 4096단계로 16배 세밀하다.'),
('07','5=00000101, 7=00000111. 7의 1의 보수는 11111000, 2의 보수는 11111001. 00000101+11111001=11111110. 최상위 비트가 1인 8비트 2의 보수 값이며, 비트를 반전하고 1을 더하면 크기가 2이므로 결과는 -2다.','13=00001101, 6=00000110, -6의 2의 보수=11111010. 00001101+11111010=1 00000111. 8비트 범위 밖의 자리올림을 버리면 00000111, 즉 7이다.'),
('08','예: 스마트 공장(센서 로그→고장 예측), 스마트 교통(차량·도로 데이터→혼잡 예측), 스마트 의료(검사·영상 데이터→진단 보조), 자율주행(카메라·라이다→객체 인식), 스마트 농업(온습도·토양 데이터→관수 제어). AI 모델은 데이터 품질과 평가 기준에 영향을 받는다.','설비 센서가 온도·진동을 수집→데이터 저장·정제→예측 모델이 이상 점수 산출→작업자 확인과 정비 일정 조정. 오탐지로 불필요한 정지가 생길 수 있으므로 경보 기준을 검증하고 사람이 최종 조치를 확인한다.'),
('09','시장 규모는 매출액인지 이용자 수인지, 국내 시장인지 기업의 해외 매출까지 포함하는지 구분한다. 수출 비중도 전체 콘텐츠 수출 중 게임의 비율인지 게임 매출 중 수출의 비율인지 확인해야 한다. 통계의 발행 기관, 조사·발표 연도, 통화·환율, 집계 기준을 명시한다. 문제로 높은 제작비, 성과 편중, 인력·노동 문제 등을 들고, 개선책으로 다양한 규모의 제작 지원, 투명한 선정·평가, 해외 유통 역량 강화 등을 논할 수 있다.','① 59%의 분모와 분자는 무엇인가? ② 3.9%는 매출, 수출, 이용자 중 무엇의 증가율인가? ③ 2024년 실적을 언제 어떤 기관이 발표했는가? ④ 23.8조 원 같은 금액은 명목·실질, 국내·해외 중 어떤 범위인가? 원문 수치만으로 현재 현황을 확정할 수 없다.'),
('10','파이썬에서 값은 타입과 상태를 가진 객체이며 이름은 객체에 바인딩된다. 수와 문자열뿐 아니라 함수, 클래스, 모듈도 객체라서 변수에 담고, 인자로 전달하고, 반환할 수 있다. 실행 중 이름이 다른 객체를 가리키도록 재바인딩할 수 있다. 메서드 호출 시에는 실제 객체의 타입을 바탕으로 속성을 찾고 호출할 함수가 정해진다.','예:\ndef a(): return 1\ndef b(): return 2\nf = a\nf = b\nprint(f())  # 2\n이름 f가 처음에는 함수 객체 a를, 나중에는 b를 참조한다. 이미 존재하는 다른 참조는 그 자체로 바뀌지 않는다.'),
('11','import는 먼저 sys.modules 캐시를 확인한다. 없으면 탐색기를 통해 모듈을 찾고 모듈 객체를 만들며, 일반적으로 실행 전에 캐시에 등록한 뒤 코드를 실행한다. 완료되면 import한 쪽의 이름이 그 객체에 바인딩된다. 이미 캐시에 있으면 보통 코드를 다시 실행하지 않고 같은 객체를 사용한다. 로더와 import 방식에 따라 세부 순서는 달라질 수 있다.','순환 import에서는 A가 B를 불러오는 동안 B가 아직 초기화되지 않은 A의 속성에 접근할 수 있다. 공통 기능을 제3의 모듈로 분리하거나, 꼭 필요한 시점까지 import를 함수 안으로 미루고 의존 방향을 단순화한다.'),
('12','CPython은 객체에 대한 참조 수가 0이 되면 대개 즉시 해제한다. 그러나 A→B와 B→A처럼 서로 참조하는 객체는 외부에서 접근할 수 없어도 각 참조 수가 0이 아닐 수 있다. 순환 가비지 컬렉터는 추적 대상 객체의 연결을 조사해 외부에서 도달할 수 없는 순환 집합을 찾아 회수한다. 언어 차원의 파이썬 객체 의미와 CPython의 메모리 관리 방식을 구분해야 한다.','외부 변수를 지워도 두 객체가 서로를 가리키므로 참조 계수가 남는다. 순환 수거기는 그 집합에 외부 경로가 없음을 확인해 회수한다. 구체적인 시점은 구현과 실행 상황에 따라 달라질 수 있다.'),
]

for i,(num,a,b) in enumerate(answers):
    if i==6:
        add(P('변환 과정 도식','h2'),SignalDiagram(),P('표본화는 시점만 이산화하고, 양자화는 진폭도 이산화합니다. 그림은 원리를 보여주는 개략도입니다.','small'))
    add(KeepTogether([P(f'{num}  핵심 문항 A','h2'),P(E(a),'answer'),P('응용 문항 B','h2'),P(E(b),'answer'),Spacer(1,3*mm)]))

add(Spacer(1,6*mm),Rule(),P('편집·검증 메모','h2'),
    P('이 책은 원문의 문항과 학습 주제를 재구성한 학습 자료입니다. 원문 9번에 적힌 2024년 시장 수치는 출처·집계 범위가 제시되지 않았으므로 해설의 사실 근거로 사용하지 않았습니다. 통계 답안에는 최신 공신력 있는 자료의 발행 기관과 기준 연도를 직접 확인해 넣으세요.','small'),
    P('파이썬 설명 검증: Python 공식 문서, The import system (docs.python.org/3/reference/import.html), Design and History FAQ의 메모리 관리 항목 (docs.python.org/3/faq/design.html).','small'))

Book(OUT).build(story)
print(OUT)
