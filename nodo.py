
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext
from livekit.plugins import (
    openai
)
import requests
from datetime import datetime, timedelta
import uuid
from livekit.api import ListParticipantsRequest
from livekit.api import LiveKitAPI
import httpx
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timezone, timedelta
from livekit.agents import ChatContext
import asyncio
import time
from livekit import rtc, api
import json
# from livekit.plugins import noise_cancellation
load_dotenv()
import logging
from typing import Optional
import re
import psycopg2 
from psycopg2 import sql
import os
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)
# DB_HOST = os.getenv('DB_HOST')
# DB_PORT = os.getenv('DB_PORT')
# DB_DATABASE = os.getenv('DB_DATABASE')
# DB_USER = os.getenv('DB_USER')
# DB_PASSWORD = os.getenv('DB_PASSWORD')
# DB_PASSWORD_PG= os.getenv('DB_PASSWORD_PG')
# DB_PG= os.getenv('DB_PG')
# DB_PORT_PG= os.getenv('DB_PORT')
# DB_USER_PG= os.getenv('DB_USER')
DB_HOST = "13.251.189.33"
DB_PORT = 33106
DB_DATABASE = "_5e5899d8398b5f7b"
DB_USER = "root"
DB_PASSWORD = "admin"
DB_PASSWORD_PG= "tks39.*AdFkrq3A9"
DB_PG= "svisor"
DB_PORT_PG= "5111"
DB_USER_PG= "postgres"

TEN_BANG_LEAD = "tabLead"
TEN_BANG_OPPORTUNITY= "tabOpportunity"
TEN_BANG_HISTORY="tabCRM Note"
TEN_BANG_EVENT="tabEvent"
TEN_BANG_EVENT_PARTICIPANT="tabEvent Participants"
API_URL = "http://103.178.231.211:8127/latest-call"

BASE_URL = "https://grand.nodo.vn/rest_api/pu/property/ai/query_object_tree"

HEADERS = {
    # Postman của bạn chỉ có 'accept: */*', nhưng ta thêm 'Content-Type'
    # để chỉ rõ rằng ta đang gửi dữ liệu dạng JSON.
    "accept": "*/*",
    "Content-Type": "application/json" 
}
BASE_URL = "https://grand.nodo.vn/rest_api/pr/property/ai/query_object_tree"
LOGIN_URL = "https://grand.nodo.vn/rest_api/pu/property/auth/login"
data=[]
# ----------------------------------------------------------------------
# API 1: Lấy danh sách dự án level = ROOT
# ----------------------------------------------------------------------
def lay_token_dang_nhap():
    """Thực hiện gọi API đăng nhập và lưu trữ Token."""
    access_token = None
    print(">>> Gọi API 0: Lấy Token Đăng nhập")

    # Payload (Body) cho API Đăng nhập
    payload_login = {
        "login": "admin",
        "password": "admin@123"
    }

    try:
        response = requests.post(
            LOGIN_URL, 
            headers=HEADERS, 
            json=payload_login,
            verify=False 
        )
        
        if response.status_code == 200:
            print("Trạng thái: Đăng nhập THÀNH CÔNG (200)")
            full_response_data = response.json()
            
            # Lấy Access Token từ phản hồi
            access_token = full_response_data.get("data").get("access_token")
            print(access_token)
            
            if access_token:
                # Cập nhật HEADERS với Authorization Token
                print("Đã lấy và lưu Token thành công.")
            else:
                print("LỖI: Không tìm thấy 'access_token' trong phản hồi.")
        else:
            print(f"Trạng thái: Đăng nhập LỖI ({response.status_code})")
            print("Nội dung lỗi:", response.text)

        return access_token
            
    except requests.exceptions.RequestException as e:
        print(f"Đã xảy ra lỗi khi gửi yêu cầu đăng nhập: {e}")
        return None,None
    
    print("-" * 50)
def lay_thong_tin_chi_tiet_du_an(duan_id):
    """Thực hiện gọi API lấy thông tin chi tiết dự án với level = SUB-TREE."""

    # Payload (Body) cho API 2
    payload_api2 = {
        "level": "SUB-TREE",
        "objectId": duan_id
    }

    try:
        response = requests.post(
            BASE_URL, 
            headers=HEADERS, 
            json=payload_api2,
            verify=False 
        )

        if response.status_code == 200:
            print("Trạng thái: THÀNH CÔNG (200)")
            print("Dữ liệu phản hồi:\n", json.dumps(response.json(), indent=4, ensure_ascii=False))
            return str(response.json())
        else:
            print(f"Trạng thái: LỖI ({response.status_code})")
            print("Nội dung lỗi:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"Đã xảy ra lỗi khi gửi yêu cầu: {e}")
        
    print("-" * 50)
async def get_latest_sip_identity_from_api():
    """
    Gọi API /latest-call để lấy số điện thoại gần nhất (SIP Identity).
    """
    try:
        # Sử dụng httpx.AsyncClient để thực hiện yêu cầu HTTP bất đồng bộ
        async with httpx.AsyncClient(timeout=5.0) as client:
            print(f"Đang gọi API: {API_URL}")
            
            # Gửi yêu cầu GET
            response = await client.get(API_URL)
            
            # Kiểm tra xem phản hồi có thành công không (mã trạng thái 200)
            if response.status_code == 200:
                data = response.json()
                # Lấy giá trị từ khóa 'latest_dialed_number'
                sip_identity = data.get("latest_dialed_number", "API_ERROR: Key not found")
                prompt = data.get("prompt", "API_ERROR: Key not found")
                duan_id = data.get("duan_id", "API_ERROR: Key not found")
                name_callee = data.get("name", "API_ERROR: Key not found")
                lead_id = data.get("lead_id", "API_ERROR: Key not found")
                print(f"Lấy thành công SIP Identity: {sip_identity}")
                return sip_identity, prompt, duan_id,name_callee,lead_id
            else:
                print(f"Lỗi API: Mã trạng thái {response.status_code} - {response.text}")
                return "API_ERROR: Bad status code"
    except httpx.RequestError as e:
        print(f"Lỗi kết nối hoặc yêu cầu: {e}")
        return "API_ERROR: Connection failed"
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return "API_ERROR: Unknown error"
def format_chat_transcript(chat_transcript):

    # Khởi tạo một danh sách trống để lưu trữ các tin nhắn đã được định dạng
    formatted_messages = []

    # Lặp qua từng 'item' (tin nhắn) trong transcript
    for item in chat_transcript.get('items', []):
        role = item.get('role')
        content_list = item.get('content', [])
        
        # Nối các phần nội dung thành một chuỗi tin nhắn. 
        # Chúng ta không cần thay thế "\n" bằng "<br>" nữa vì đây là JSON, không phải HTML.
        message = " ".join(content_list)

        # Xác định vai trò đã được dịch
        if role == 'assistant':
            speaker = "agent"
        elif role == 'user':  # Giả định 'user' là 'khách hàng'
            speaker = "khách hàng"
        else:
            # Xử lý các vai trò không xác định (có thể bỏ qua hoặc gán vai trò mặc định)
            speaker = "unknown"
            
        # Tạo một dictionary cho tin nhắn hiện tại
        message_object = {
            "speaker": speaker,
            "message": message
        }

        # Thêm dictionary này vào danh sách
        formatted_messages.append(message_object)

    # Chuyển danh sách các đối tượng tin nhắn thành một chuỗi JSON
    # 'indent=4' giúp chuỗi JSON dễ đọc hơn (tùy chọn)
    json_output = json.dumps(formatted_messages, indent=4, ensure_ascii=False)
    
    return json_output
def doc_du_lieu(caller_number, status_call, summary,chat_transcript_v2,time_start_call,lead_id):
    access_token=lay_token_dang_nhap()
    tz_plus7 = timezone(timedelta(hours=7))
    time_end_dt = datetime.now(tz_plus7)
    time_end_formatted = time_end_dt.strftime("%d-%m-%Y %H:%M:%S")
    auth='Bearer '+access_token
    url = 'https://grand.nodo.vn//rest_api/pr/property/lead/call_logs'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': auth,
        'Cookie': 'frontend_lang=en_US; session_id=d20f6a6ec83474bc70d2c86bc080c7a483bf3281'
    }

    payload = {
        "status_call": int(status_call),
        "lead_id": lead_id,
        "time_start_call": time_start_call,
        "time_end_call": time_end_formatted,
        "note": summary,
        "context_call_json": chat_transcript_v2, 
        "bot_name": "AI Assistant"
    }
    response = requests.post(url, headers=headers, json=payload)
    print(response)

def luu_vao_postgres(caller_number, status_call, summary,chat_transcript_v2,time_start_call,lead_id):
    """Lưu dữ liệu cuộc gọi vào bảng nodo_outbound.nodo_history."""
    conn = None
    try:
        # 1. Thiết lập kết nối
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT_PG,
            database=DB_PG,
            user=DB_USER_PG,
            password=DB_PASSWORD_PG
        )
        cur = conn.cursor()

        # 2. Xây dựng lệnh SQL INSERT
        # Chú ý sử dụng %s placeholders để tránh SQL Injection
        insert_query = sql.SQL("""
            INSERT INTO nodo_outbound.nodo_history (
                id, caller_number, status_call, note, context_call_json, 
                time_start_call, lead_id, time_end_call
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """)
        
        # Tạo thời điểm kết thúc cuộc gọi cho bản ghi DB
        tz_plus7 = timezone(timedelta(hours=7))
        time_end_dt = datetime.now(tz_plus7)
        time_end_formatted = time_end_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 3. Chuẩn bị dữ liệu để chèn
        # Đảm bảo thứ tự dữ liệu khớp với thứ tự các cột trong câu lệnh INSERT
        data_to_insert = (
            str(uuid.uuid4()),
            caller_number,
            status_call,
            summary,
            chat_transcript_v2,
            time_start_call,
            lead_id,
            time_end_formatted
        )
        
        # 4. Thực thi và Commit
        cur.execute(insert_query, data_to_insert)
        conn.commit()
        print("\n[DB] Đã lưu dữ liệu vào PostgreSQL thành công.")

    except (Exception, psycopg2.Error) as error:
        print(f"\n[DB] Lỗi khi kết nối hoặc ghi dữ liệu PostgreSQL: {error}")
    finally:
        # 5. Đóng kết nối
        if conn:
            cur.close()
            conn.close()


async def init_participants(room):
    async with LiveKitAPI() as lkapi:
        res = await lkapi.room.list_participants(
            ListParticipantsRequest(room=room.name)
        )
        for participant in res.participants:
            if participant.identity.startswith("sip_"):
                sip_identity = participant.identity.split("_")[1]
                return sip_identity

        # Nếu không tìm thấy participant nào có identity bắt đầu bằng "sip_"
        print("Không tìm thấy participant có identity dạng 'sip_'.")
        return None

def get_call_uuid(con, call_to_transfer,cid_num):
    """
    Tìm UUID của cuộc gọi dựa trên số điện thoại gọi đi hoặc gọi đến.
    Lệnh 'show calls' sẽ liệt kê tất cả các cuộc gọi đang hoạt động.
    Chúng ta sẽ phân tích output để tìm UUID của cuộc gọi cần chuyển.
    
    Lưu ý: Cách này có thể không hiệu quả với số lượng cuộc gọi lớn.
    """
    
    # Thực hiện lệnh 'show calls' để lấy danh sách các cuộc gọi
    response = con.api('show calls as json')
    
    # Phân tích phản hồi JSON
    try:
        calls_data = eval(response.getBody())
        for call in calls_data.get('rows', []): # Chú ý: Dữ liệu nằm trong khóa 'rows'
            # Kiểm tra xem số cần tìm có khớp với 'dest' (destination) hoặc 'b_dest' (bridged destination) hay không.
            if (call.get('dest') == call_to_transfer and call.get('cid_num') == cid_num):
                uuid = call.get('uuid')
                return uuid
            elif (call.get('b_dest') == call_to_transfer and call.get('b_cid_num') == cid_num):
                uuid = call.get('b_uuid')
                return uuid
    except Exception as e:
        print(f"Lỗi khi phân tích dữ liệu JSON: {e}")
        return None
        
    print(f"Không tìm thấy UUID nào cho cuộc gọi đến {call_to_transfer}.")
    return None
async def analyze_and_save_opportunity(room, session,caller_number,time_start_call,lead_id):
    """
    Phân tích lịch sử cuộc gọi và lưu thông tin cơ hội vào DB.
    """
    llm = openai.LLM(model="gpt-4o-mini")
    # 1. Đọc lịch sử trò chuyện
    history = session.history
    
    # chat_transcript = str(history.to_dict())
    # print(chat_transcript)
    items_list = history.to_dict().get('items', [])
    filtered_items = []
    for item in items_list:
        # Chúng ta chỉ quan tâm đến các mục có 'type' là 'message'
        if item.get('type') == 'message':
            # 3. Thêm mục tin nhắn vào danh sách đã lọc
            filtered_items.append(item)
    result = {
        'items': filtered_items
    }
    chat_transcript_v2=format_chat_transcript(result)
    chat_transcript = str(result)
    # print(chat_transcript)
    utc_now = datetime.now(timezone.utc)

    # Tạo múi giờ +7
    tz_plus7 = timezone(timedelta(hours=7))

    # Chuyển sang múi giờ +7
    local_time = utc_now.astimezone(tz_plus7)
    formatted_time_vn = local_time.strftime("%A, %d/%m/%Y %H:%M:%S")

    # system_prompt = f"""
    # Bạn là một chuyên gia phân tích cuộc gọi.
    # Dưới đây là lịch sử trò chuyện giữa nhân viên tư vấn và khách hàng:
    # ---
    # {chat_transcript}
    # ---

    # Nhiệm vụ:
    # 1. Phân loại mức độ quan tâm của khách hàng:
    #    - **'103'** nếu khách hàng đã thể hiện sự quan tâm đến sản phẩm đang được tiếp thị (ví dụ: đặt câu hỏi sâu, thể hiện ý định mua, hoặc có phản hồi tích cực).
    #    - **'105'** nếu khách hàng không quan tâm đến sản phẩm đang được tiếp thị.
    #    - **'104'** nếu khách hàng có báo gọi lại sau.
    # 2. Tóm tắt những sản phẩm mà khách hàng quan tâm, không quan tâm.
    # Trả về kết quả đúng định dạng JSON sau:
    # {{
    #    "status_call": "103" hoặc "104" hoặc "105",
    #    "summary": Tóm tắt ngắn gọn (ví dụ: "khách hàng quan tâm đến sản phẩm A, không quan tâm đến sản phẩm B").
    # }}

    # Không thêm bất kỳ giải thích nào khác ngoài JSON hợp lệ.
    # """
    system_prompt = f"""
    Bạn là một chuyên gia phân tích cuộc gọi.
    Dưới đây là lịch sử trò chuyện giữa nhân viên tư vấn và khách hàng:
    ---
    {chat_transcript}
    ---

    Nhiệm vụ:
    1. Phân loại mức độ quan tâm của khách hàng:
       - **'103'** nếu khách hàng đã thể hiện sự quan tâm đến sản phẩm đang được tiếp thị (ví dụ: đặt câu hỏi sâu, thể hiện ý định mua, hoặc có phản hồi tích cực).
       - **'105'** nếu khách hàng không quan tâm đến sản phẩm đang được tiếp thị.
       - **'104'** nếu khách hàng có báo gọi lại sau.
    2. Tóm tắt những sản phẩm mà khách hàng quan tâm, không quan tâm.
    Trả về kết quả đúng định dạng JSON sau:
    {{
       "status_call": "103" hoặc "104" hoặc "105",
       "summary": dạng string text, tóm tắt cuộc gọi để lấy được các thông tin về email, số điện thoại, tên dự án, loại hình bất động sản, mục đích sử dụng, vị trí, loại căn hộ, hướng, ngân sách, hình thứ thanh toán, lịch hẹn. Những thông tin không đề cập thì không cần có, nhưng nếu được nhắc đến thì phải tóm tắt thông tin chính xác.
    }}

    Không thêm bất kỳ giải thích nào khác ngoài JSON hợp lệ.
    """


    chat_ctx = ChatContext()
    chat_ctx.add_message(role="system", content=system_prompt)
    llm_stream = llm.chat(chat_ctx=chat_ctx)

    llm_response_full = ""
    async for chunk in llm_stream:
        if chunk and chunk.delta and chunk.delta.content:
            llm_response_full += chunk.delta.content

    print("LLM raw:", llm_response_full)

    try:
        parsed = json.loads(llm_response_full)
        status_call = parsed.get("status_call")
        summary = parsed.get("summary")

    except Exception as e:
        print(f"Lỗi parse JSON từ LLM: {e}")
        status_call = "105"
        summary = None

    if status_call not in ['103', '104','105']:
        print(f"LLM trả về giá trị không hợp lệ: {status_call}. Mặc định là 'Needs Analysis'.")
        status_call = '105'

    print(f"Đã xác định được status_call: {status_call}")
    print(f"Tóm tắt: {summary}")

    # 4. Lưu vào DB
    if caller_number != '':
        print(f"Số điện thoại người gọi là: {caller_number}. Tiến hành lưu vào DB.")
        await asyncio.gather(
            asyncio.to_thread(doc_du_lieu, caller_number, status_call, summary, chat_transcript_v2, time_start_call, lead_id),
            asyncio.to_thread(luu_vao_postgres, caller_number, status_call, summary, chat_transcript_v2, time_start_call, lead_id)
        )
        # doc_du_lieu(caller_number, status_call, summary,chat_transcript_v2,time_start_call,lead_id)
        # luu_vao_postgres(caller_number, status_call, summary,chat_transcript_v2,time_start_call,lead_id)
        print(time_start_call)
    else:
        print("Không tìm thấy số điện thoại người gọi (sip_identity), không thể lưu vào DB.")
    

async def get_db_from_lead(phone_number: str) -> str | None:  
    # Hàm đồng bộ để thực hiện kết nối và truy vấn DB
    def sync_db_lookup(num_phone):
        connection = None
        website = "7a24ed17-fb8e-4fbe-a544-a3d4aa322da3"
        doc_id = "1dAWoUb3LghdUI2BZbCcQkWuhxpjEgIjB"
        lead_name= "Không được cung cấp"
        try:
            # 1. Kết nối DB
            connection = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_DATABASE,
                user=DB_USER,
                password=DB_PASSWORD
            )
            
            if connection and connection.is_connected():
                cursor = connection.cursor()
                
                # 2. Câu truy vấn SQL
                query = f"SELECT website,fax,lead_name FROM {TEN_BANG_LEAD} WHERE phone = %s LIMIT 1"
                
                # 3. Thực thi truy vấn
                cursor.execute(query, (num_phone,))
                
                # 4. Lấy kết quả đầu tiên
                result = cursor.fetchone()
                
                if result :
                    # Lấy giá trị cột 'website' (result là tuple, giá trị ở index 0)
                    website = result[0]
                    doc_id = result[1]
                    lead_name = result[2]
                    print(f"Tìm thấy website '{website}' cho số điện thoại {num_phone}.")
                    print(f"Tìm thấy fax '{doc_id}' cho số điện thoại {num_phone}.")
                    print(f"Tìm thấy name '{lead_name}' cho số điện thoại {num_phone}.")
                else:
                    print(f"Không tìm thấy bản ghi Lead với số điện thoại {num_phone}.")
                    
        except Error as e:
            print(f"Lỗi MySQL khi đọc website: {e}")
        except Exception as e:
            print(f"Lỗi không xác định khi truy vấn DB: {e}")
        finally:
            # 5. Đóng kết nối
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
                
        return website,doc_id,lead_name

    # Chạy hàm đồng bộ trong một luồng riêng để không chặn asyncio event loop
    return await asyncio.to_thread(sync_db_lookup, phone_number)
async def get_content(doc_id):
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    response = requests.get(url)
    if response.status_code == 200:
        text = response.text
        return text
    else:
        print(f"Failed to fetch document. Status code: {response.status_code}")
        return ""
class Assistant(Agent):
    def __init__(self, content: str,room,ctx,formatted_time_vn) -> None:

        super().__init__(instructions=f"""
        Dưới đây là chỉ dẫn chi tiết về bạn là ai, và những gì bạn phải làm theo:
        {content}

        *****Chú ý:
        - Bạn đang nói chuyện với người có tên {ctx.log_context_fields.get("name_callee")}. Hiện tại đang là {formatted_time_vn}
        - Câu chào hỏi ban đầu rất quan trọng, bạn phải làm đúng theo hướng dẫn, không được thiếu hay sai sót.
        - Luôn luôn sử dụng tool get_info() để lấy thông tin khi khách hàng hỏi sâu về các dự án hoặc khi cần lấy thông tin từ cơ sở dữ liệu.
        - Luôn yêu cầu khách vui lòng chờ nếu như bạn bắt đầu sử dụng tool get_info(), sau khi sử dụng xong phải ngay lập tức trả lời cho khách hàng 1 cách nhanh nhất.
        - Nhớ thật kỹ trước khi sử dụng tool luôn luôn phải nói với khách hàng xin chờ trong giây lát, sử dụng xong phải trả lời tiếp khách hàng ngay lập tức.
        - Không cần thông báo về việc sẽ sử dụng tool cho khách hàng nhưng phải nói với khách hàng xin chờ trong giây lát để tìm kiếm thông tin.
        - Bạn phải lấy thông tin cần thiết bằng tool get_info() để trả lời các câu hỏi của khách hàng nếu cần. Và phải dùng thông tin và các dòng chat trước đó để trả lời, không được trả lời sai thông tin.
        - Bạn phải lấy thông tin cần thiết bằng tool get_info() nếu cần lấy thông tin từ cơ sở dữ liệu.
        - Phải cẩn thận với lời chào của bạn theo đúng hướng dẫn.
        - Dùng tool ask_other_project() để lấy thông tin và trả lời câu hỏi về các dự án khác nếu như người dùng hỏi về ngoài dự án khác, ngoài dự án dự án đang được giới thiệu.
        - Tool hang_up được dùng sau khi chào tạm biệt khách hàng. 
        - Tool phải được dùng sau khi nói hết câu tạm biệt. Không được dùng tool trong khi đang nói.
        """)
        self.room=room
        self.ctx=ctx
    @function_tool
    async def get_info(self, context: RunContext,question: str) -> str:
        """
        Lấy thông tin liên quan từ cơ sở kiến thức bằng cách gọi API RAG.
        Sử dụng tool này khi khách hàng hỏi những câu hỏi về dự án đang giới thiệu.
        Sử dụng tool này khi cần lấy thông tin từ cơ sở dữ liệu.

        Tham số:
        question (str): Câu hỏi của khách hàng cần được tìm kiếm trong cơ sở dữ liệu.
        """
        url = "http://13.251.189.33:8117/ask/category"
        category_filter = {"project_id": self.ctx.log_context_fields.get("duan_id")}
        category_json_string = json.dumps(category_filter)
        # Các tham số cần thiết cho API của bạn.
        payload = {
            "question": question,
            "top_k": 5,
            "table_name": "nodo_file_emb",
            "category": category_json_string,
            "rerank": 3
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(url, data=payload, timeout=20.0)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                context_content = "\n---\n".join([
                    f"Tài liệu {i+1} (score: {r.get('score')}):\n{r.get('content')}"
                    for i, r in enumerate(results)
                    if r.get('content')
                ])
                if context_content:
                    return f"Đã tìm thấy thông tin: {context_content}"
                else:
                    return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
            else:
                error_details = response.text 
                return f"Đã xảy ra lỗi khi tìm kiếm thông tin. Mã lỗi: {response.status_code}. Chi tiết từ API: {error_details[:200]}..."

        except httpx.ConnectTimeout:
            return "Đã hết thời gian chờ kết nối đến máy chủ RAG. Vui lòng thử lại sau."
        except httpx.ConnectError:
            return "Không thể kết nối đến máy chủ RAG. Vui lòng kiểm tra lại địa chỉ."

    @function_tool
    async def get_apartment_info(self, context: RunContext,location: str = "",property_type:str = "", area:str= "",direction:str= "",purpose:str= "",num_rooms:str= "",price:str= "",num_floors:str= "") -> str:
        """
        Lấy thông tin liên quan từ cơ sở kiến thức bằng cách gọi API RAG.
        Sử dụng tool này khi khách hàng hỏi những câu hỏi về chi tiết căn hộ trong dự án hoặc bạn muốn giới thiệu căn hộ cho khách hàng.
        Phải nhập toàn bộ tham số, những tham số nào không được khách hàng nhắc đến thì dùng chuỗi "" thay thế.

        Tham số:
        location: Căn hộ thuộc thành phố nào.
        property_type: Loại hình dự án (ví dụ: thấp tầng hay cao tầng)
        area: Diện tích căn hộ theo m2(ví dụ: 145 )
        direction: Hướng căn hộ (ví dụ: Đông, Tây, Nam , Bắc)
        purpose: Mục đích sử dụng (ví dụ: cho thuê, đầu tư, để ở)
        num_rooms: số phòng trong căn hộ (ví dụ: 1,3,4,...)
        price: giá căn hộ (ví dụ: 64302628767)
        num_floors: số tầng của căn hộ (ví dụ: 1,3,5,2,...)
        """
        def parse_number(s: Optional[str]) -> Optional[float]:
            if not s:
                return None
            # tìm số thập phân/ nguyên trong chuỗi (ví dụ: "145 m2" -> 145, "64,302,628,767" -> 64302628767)
            try:
                # loại bỏ dấu phẩy, dấu chấm nhóm hàng ngàn
                normalized = re.sub(r"[,\s]", "", s)
                # tìm số có dấu thập phân hoặc nguyên
                m = re.search(r"[-+]?\d*\.?\d+", normalized)
                if m:
                    val = m.group(0)
                    # nếu có dấu '.' -> float, else int-> float
                    return float(val)
            except Exception:
                return None
            return None
        area_val = parse_number(area)
        price_val = parse_number(price)
        num_rooms_val = parse_number(num_rooms)
        num_floors_val = parse_number(num_floors)
        url = "http://13.251.189.33:8117/apartments/search/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        all_params = {
            "vi_tri": location,
            "loai_hinh": property_type,
            "dien_tich": area_val,
            "huong": direction,
            "muc_dich_mua": purpose,
            # Ép kiểu int nếu giá trị có, hoặc giữ nguyên None
            "so_phong": int(num_rooms_val) if num_rooms_val is not None else None,
            "gia": price_val,
            "so_tang": int(num_floors_val) if num_floors_val is not None else None,
            "project_id": self.ctx.log_context_fields.get("duan_id")
        }
        
        
        payload = {}
        for key, value in all_params.items():
            if isinstance(value, str) and value != "":
                payload[key] = value
            elif value is not None:
                # Bao gồm các giá trị số (float, int) và project_id (có thể là string hoặc None, nếu là None sẽ bị loại)
                payload[key] = value
                
        # Xử lý đặc biệt cho project_id nếu nó là None, để đảm bảo nó không được thêm vào
        if all_params.get("project_id") is None:
            payload.pop("project_id", None)
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                mota_apart=""
                data = response.json()
                mo_ta_list = data.get("mo_ta_list", [])
                for i, mo_ta in enumerate(mo_ta_list, start=1):
                    mota=f"""Căn hộ {i} có mô tả là {mo_ta} \n"""
                    mota_apart+=mota
                return mota_apart
            else:
                error_details = response.text 
                return f"Đã xảy ra lỗi khi tìm kiếm thông tin. Mã lỗi: {response.status_code}. Chi tiết từ API: {error_details[:200]}..."

        except httpx.ConnectTimeout:
            return "Đã hết thời gian chờ kết nối đến máy chủ RAG. Vui lòng thử lại sau."
        except httpx.ConnectError:
            return "Không thể kết nối đến máy chủ RAG. Vui lòng kiểm tra lại địa chỉ."

    @function_tool
    async def ask_other_project(self, context: RunContext,question: str) -> str:
        """
        Lấy thông tin liên quan từ cơ sở kiến thức bằng cách gọi API RAG.
        Sử dụng tool này khi khách hàng hỏi những câu hỏi cụ thể về hợp đồng.

        Tham số:
        question (str): Câu hỏi của khách hàng cần được tìm kiếm trong cơ sở dữ liệu.
        """
        url = "http://13.251.189.33:5113/ask"

        # Các tham số cần thiết cho API của bạn.
        payload = {
            "question": question,
            "top_k": 5,
            "table_name": "NODO0711",
            "category": "string",
            "rerank": 3
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(url, data=payload, timeout=20.0)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                context_content = "\n---\n".join([
                    f"Tài liệu {i+1} (score: {r.get('score')}):\n{r.get('content')}"
                    for i, r in enumerate(results)
                    if r.get('content')
                ])
                if context_content:
                    return f"Đã tìm thấy thông tin: {context_content}"
                else:
                    return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
            else:
                error_details = response.text 
                return f"Đã xảy ra lỗi khi tìm kiếm thông tin. Mã lỗi: {response.status_code}. Chi tiết từ API: {error_details[:200]}..."

        except httpx.ConnectTimeout:
            return "Đã hết thời gian chờ kết nối đến máy chủ RAG. Vui lòng thử lại sau."
        except httpx.ConnectError:
            return "Không thể kết nối đến máy chủ RAG. Vui lòng kiểm tra lại địa chỉ."
        

    @function_tool
    async def hang_up(self, context: RunContext):
        """
        Mục đích tool này để ngắt cuộc gọi sau khi chào tạm biệt khách hàng.
        Tool được dùng sau khi nói xong lời chào tạm biệt với khách hàng.
        """
        await asyncio.sleep(8)
        await self.ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=self.ctx.room.name,
        )
    )

async def entrypoint(ctx: agents.JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    utc_now = datetime.now(timezone.utc)

    # Tạo múi giờ +7
    tz_plus7 = timezone(timedelta(hours=7))

    # Chuyển sang múi giờ +7
    local_time = utc_now.astimezone(tz_plus7)
    formatted_time_vn = local_time.strftime("%A, %d/%m/%Y %H:%M:%S")
    time_start_formatted = local_time.strftime("%d-%m-%Y %H:%M:%S")
    sip_identity,duan_id,name_callee,lead_id = "","","",""
    content = ""
    ctx.log_context_fields = {
        "caller_number": sip_identity,
        "duan_id": duan_id,
        "time_start_formatted":time_start_formatted,
        "name_callee":name_callee,
        "lead_id": lead_id,
    }
    model="gpt-4o-realtime-preview" 
    await ctx.connect()
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model=model,
            voice="shimmer",
            speed=1.3,
        ),
    )
    await session.start(
        room=ctx.room,
        agent=Assistant(content=content,room=ctx.room,ctx=ctx,formatted_time_vn=formatted_time_vn),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            #noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    await session.generate_reply(
        instructions=f"""
        Dưới đây là chỉ dẫn chi tiết về bạn là ai, và những gì bạn phải làm theo:
        {content}

        *****Chú ý:
        - Bạn đang nói chuyện với người có tên {ctx.log_context_fields.get("name_callee")}. Hiện tại đang là {formatted_time_vn}
        - Câu chào hỏi ban đầu rất quan trọng, bạn phải làm đúng theo hướng dẫn, không được thiếu hay sai sót.
        - Luôn luôn sử dụng tool get_info() để lấy thông tin khi khách hàng hỏi sâu về các dự án hoặc khi cần lấy thông tin từ cơ sở dữ liệu để tư vấn cho khách hàng.
        - Luôn yêu cầu khách vui lòng chờ nếu như bạn bắt đầu sử dụng tool get_info(), sau khi sử dụng xong phải ngay lập tức trả lời cho khách hàng 1 cách nhanh nhất.
        - Nhớ thật kỹ trước khi sử dụng tool luôn luôn phải nói với khách hàng xin chờ trong giây lát, sử dụng xong phải trả lời tiếp khách hàng ngay lập tức.
        - Không cần thông báo về việc sẽ sử dụng tool cho khách hàng nhưng phải nói với khách hàng xin chờ trong giây lát để tìm kiếm thông tin.
        - Bạn phải lấy thông tin cần thiết bằng tool get_info() để trả lời các câu hỏi của khách hàng nếu cần. Và phải dùng thông tin và các dòng chat trước đó để trả lời, không được trả lời sai thông tin.
        - Bạn phải lấy thông tin cần thiết bằng tool get_info() nếu cần lấy thông tin từ cơ sở dữ liệu.
        - Phải cẩn thận với lời chào của bạn theo đúng hướng dẫn.
        - Dùng tool ask_other_project() để lấy thông tin và trả lời câu hỏi về các dự án khác nếu như người dùng hỏi về ngoài dự án khác, ngoài dự án dự án đang được giới thiệu.
        - Tool hang_up được dùng sau khi chào tạm biệt khách hàng. 
        - Tool phải được dùng sau khi nói hết câu tạm biệt. Không được dùng tool trong khi đang nói.
        """)
    async def on_shutdown():
        caller_number = ctx.log_context_fields.get("caller_number")
        time_start_call = ctx.log_context_fields.get("time_start_formatted")
        lead_id = ctx.log_context_fields.get("lead_id")
        # 2. Phân tích bằng LLM để xác định opportunity
        await analyze_and_save_opportunity(ctx.room,session,caller_number,time_start_call,lead_id)
    # Gắn callback
    ctx.add_shutdown_callback(on_shutdown)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint,agent_name="vin-outbound-caller"))


# - Sử dụng tool get_apartment_info() để lấy thông tin căn hộ sau khi hỏi và lấy được đầy đủ thông tin về căn hộ mà khách hàng mong muốn.
# - Khi dùng tool get_apartment_info() phải nhập toàn bộ tham số, những tham số nào không được khách hàng nhắc đến thì dùng chuỗi "" thay thế.
# - Luôn yêu cầu khách vui lòng chờ nếu như bạn bắt đầu sử dụng tool get_info(), sau khi sử dụng xong phải ngay lập tức trả lời cho khách hàng 1 cách nhanh nhất.
# - Trước Khi dùng tool get_apartment_info() để tìm căn hộ, phải tổng hợp lại và nói cho khách biết những thông tin về căn hộ mà bạn định đưa vào tool.