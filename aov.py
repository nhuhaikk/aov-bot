import os
import shutil
import logging
import asyncio
import zipfile
import time
import UnityPy_AOV
from PIL import Image
from UnityPy_AOV.enums import TextureFormat
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Cấu hình log để dễ theo dõi lỗi
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8815828923:AAFN-qJ2gC9Kru3JWaPngmUQbgJG5927L1w"
WORKDIR = "FolderBotAov"

os.makedirs(WORKDIR, exist_ok=True)

# Biến toàn cục kiểm soát tần suất edit tin nhắn
LAST_EDIT_TIME = 0
# Lưu trạng thái lựa chọn chức năng của người dùng {user_id: "chức_năng"}
USER_STATES = {}

async def progress_tg(context, status_msg, file, done, total, start_time, last=[-1]):
    """Hàm hiển thị Progress thông minh - Khắc phục triệt để lỗi nghẽn và Timed Out"""
    global LAST_EDIT_TIME
    percent = int((done / total) * 100)
    current_time = time.time()

    if (percent != last[0] and percent % 5 == 0 and current_time - LAST_EDIT_TIME > 1.5) or done == total:
        last[0] = percent
        LAST_EDIT_TIME = current_time
        
        elapsed = current_time - start_time
        speed = done / elapsed if elapsed > 0 else 0
        remain = (total - done) / speed if speed > 0 else 0
        remain_str = f"{remain:.1f}s" if remain > 0 else "0s"
        
        bar_length = 15
        filled_length = int(bar_length * done // total)
        bar = '■' * filled_length + '□' * (bar_length - filled_length)
        
        progress_text = (
            f"<code>"
            f"File: {file}\n"
            f"-------------------------\n"
            f"Tiến độ : {bar} {percent}%\n"
            f"Đã xong : {done}/{total} files\n"
            f"Tốc độ  : {speed:.1f} file/s\n"
            f"Còn lại : {remain_str}\n"
            f"</code>"
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id,
                message_id=status_msg.message_id,
                text=f"<b>HỆ THỐNG ĐANG XỬ LÝ DỮ LIỆU...</b>\n\n{progress_text}",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start hiển thị Menu chức năng"""
    user_id = update.effective_user.id
    USER_STATES.pop(user_id, None) # Reset trạng thái khi bấm start
    
    keyboard = [
        [InlineKeyboardButton("MOD AOV", callback_data="menu_mod_skin"),
        InlineKeyboardButton("MOD ASSETBUNDLE", callback_data="menu_mod_assetbundle")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Xin chào {update.effective_user.first_name}!\n"
        "Tôi là bot Aov được phát triển bởi @inhuhai!\n\n"
        "<b>CHỌN CHỨC NĂNG</b>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng chọn nút trên Menu"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Bấm nút quay lại: Chuyển đổi trực tiếp tin nhắn hiện tại về Menu chính, không xóa không gửi mới
    if query.data == "menu_back":
        USER_STATES.pop(user_id, None) # Xóa trạng thái cũ để tránh lỗi gửi nhầm file
        keyboard = [
            [InlineKeyboardButton("MOD AOV", callback_data="menu_mod_skin"),
            InlineKeyboardButton("MOD ASSETBUNDLE", callback_data="menu_mod_assetbundle")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Xin chào {update.effective_user.first_name}!\n"
            "Tôi là bot Aov được phát triển bởi @inhuhai!\n\n"
            "<b>CHỌN CHỨC NĂNG</b>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return

    if query.data == "menu_mod_assetbundle":
        USER_STATES[user_id] = "mod_assetbundle"
        keyboard = [[InlineKeyboardButton("Quay lại Menu chính", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "<b>CHỨC NĂNG: MOD ASSETBUNDLE</b>\n\n"
            "Gửi file <code>.assetbundle</code> để Extract (Xuất ảnh Texture).\n"
            "Gửi file <code>.zip</code> chứa texture đã sửa + assetbundle gốc để Import.\n\n",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    elif query.data == "menu_mod_skin":
        USER_STATES[user_id] = "mod_skin"
        keyboard = [[InlineKeyboardButton("Quay lại Menu chính", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "<b>Thông báo:</b> Tính năng <b>MOD AOV (Mod Skin)</b> đang trong quá trình phát triển và sẽ sớm ra mắt!\n\n",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi người dùng gửi file"""
    user_id = update.effective_user.id
    state = USER_STATES.get(user_id)
    
    # Nếu người dùng chưa chọn chức năng nào
    if not state:
        await update.message.reply_text("Vui lòng sử dụng lệnh /start và chọn chức năng trước khi gửi file.")
        return
        
    # Nhánh chức năng Mod Skin
    if state == "mod_skin":
        await update.message.reply_text("Tính năng Mod Skin đang phát triển, hiện tại chưa thể xử lý file này.")
        return

    # Nhánh chức năng Mod AssetBundle
    if state == "mod_assetbundle":
        doc = update.message.document
        file_name = doc.file_name
        
        user_dir = os.path.join(WORKDIR, str(user_id))
        shutil.rmtree(user_dir, ignore_errors=True) 
        os.makedirs(user_dir, exist_ok=True)
        
        status_msg = await update.message.reply_text("Đang tải file về server...")
        tg_file = await context.bot.get_file(doc.file_id)
        file_path = os.path.join(user_dir, file_name)
        await tg_file.download_to_drive(file_path)

        # TRƯỜNG HỢP 1: Extract
        if file_name.endswith(".assetbundle"):
            try:
                zip_out = await process_extract_tg(user_dir, file_path, file_name, status_msg, context)
                
                if zip_out:
                    await status_msg.edit_text("Đang gửi file Zip chứa Textures...")
                    await update.message.reply_document(
                        document=open(zip_out, 'rb'), 
                        caption="Thành công! Giải nén file ZIP này, chỉnh sửa các file ảnh trong thư mục `Texture2D`, sau đó nén ZIP lại và gửi lại cho Bot để Import nhé."
                    )
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
                else:
                    await status_msg.edit_text("File AssetBundle này không chứa Texture2D nào.")
            except Exception as e:
                await status_msg.edit_text(f"Có lỗi xảy ra khi Extract: {str(e)}")
                
        # TRƯỜNG HỢP 2: Import
        elif file_name.endswith(".zip"):
            try:
                mod_bundle = await process_import_tg(user_dir, file_path, status_msg, context)
                
                if mod_bundle:
                    await status_msg.edit_text("Đang gửi file đã Mod...")
                    await update.message.reply_document(
                        document=open(mod_bundle, 'rb'), 
                        caption="Đây là file AssetBundle đã được cập nhật Texture mới của bạn!\nXoá đuôi _mod sau đó copy dán vào data game và tận hưởng 😏."
                    )
                    try:
                        await status_msg.delete()
                    except Exception:
                        pass
                else:
                    await status_msg.edit_text("Không tìm thấy cấu trúc file hợp lệ trong Zip. File Zip phải chứa file gốc và thư mục `Texture2D` chứa ảnh.")
            except Exception as e:
                await status_msg.edit_text(f"Có lỗi xảy ra khi Import: {str(e)}")
                
        else:
            await status_msg.edit_text("Định dạng file không được hỗ trợ. Vui lòng chỉ gửi file `.assetbundle` hoặc `.zip`.")

        shutil.rmtree(user_dir, ignore_errors=True)

async def process_extract_tg(user_dir, bundle_path, file_name, status_msg, context):
    """Hàm xử lý Extract kết hợp giao diện progress"""
    env = UnityPy_AOV.load(bundle_path)
    textures = [obj for obj in env.objects if obj.type.name == "Texture2D"]
    total = len(textures)
    
    if not textures:
        return None
        
    base_name = os.path.splitext(file_name)[0]
    texture_folder = os.path.join(user_dir, "Texture2D", base_name)
    os.makedirs(texture_folder, exist_ok=True)
    
    done = 0
    start_time = time.time()
    last = [-1]
    
    for obj in textures:
        try:
            data = obj.read()
            dest = os.path.join(texture_folder, f"{data.m_Name}.png")
            img = data.image.convert("RGBA")
            img.save(dest)
        except:
            pass
        done += 1
        
        await progress_tg(context, status_msg, file_name, done, total, start_time, last)
        await asyncio.sleep(0.001)
            
    await status_msg.edit_text("Đang đóng gói dữ liệu thành file ZIP...")
    
    zip_path = os.path.join(user_dir, f"{base_name}_extracted.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(bundle_path, file_name)
        for root, dirs, files in os.walk(os.path.join(user_dir, "Texture2D")):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, user_dir)
                zipf.write(full_p, rel_p)
                
    return zip_path

async def process_import_tg(user_dir, zip_path, status_msg, context):
    """Hàm xử lý Import kết hợp giao diện progress"""
    extract_zip_dir = os.path.join(user_dir, "extracted_zip")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_zip_dir)
        
    bundle_file = None
    for item in os.listdir(extract_zip_dir):
        if item.endswith(".assetbundle") and not item.endswith("_mod.assetbundle"):
            bundle_file = item
            break
            
    if not bundle_file:
        return None
        
    bundle_path = os.path.join(extract_zip_dir, bundle_file)
    base_name = os.path.splitext(bundle_file)[0]
    texture_folder = os.path.join(extract_zip_dir, "Texture2D", base_name)
    
    if not os.path.exists(texture_folder):
        return None
        
    env = UnityPy_AOV.load(bundle_path)
    textures = [obj for obj in env.objects if obj.type.name == "Texture2D"]
    total = len(textures)
    
    if not textures:
        return None
        
    done = 0
    start_time = time.time()
    last = [-1]
    
    for obj in textures:
        try:
            data = obj.read()
            fp = os.path.join(texture_folder, f"{data.m_Name}.png")
            
            if os.path.exists(fp):
                pil_img = Image.open(fp).convert("RGBA")
                data.set_image(pil_img, TextureFormat.RGBA32)
                data.save()
        except:
            pass
        done += 1
        
        await progress_tg(context, status_msg, bundle_file, done, total, start_time, last)
        await asyncio.sleep(0.001)
            
    await status_msg.edit_text("Đang cấu trúc và nén lại file AssetBundle...")
    
    output_bundle_name = f"{base_name}_mod.assetbundle"
    output_bundle_path = os.path.join(user_dir, output_bundle_name)
    
    with open(output_bundle_path, "wb") as f:
        f.write(env.file.save("lz4"))
        
    return output_bundle_path

def main():
    """Khởi tạo và chạy bot"""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot đang chạy... Nhấn Ctrl+C để dừng.")
    application.run_polling()

if __name__ == "__main__":
    main()
