
# -*- coding: utf-8 -*-
"""
Centralized preset registry for Gemini Story Studio.
Each preset defines tone/style/world/tropes and audio-first hints
that will be injected into prompt builders.
"""

PRESETS = {
    "Trung Quốc · Xuyên Không · Ngôn Tình · Hệ Thống": {
        "tagline": "Xuyên không – báo thù – cặp đôi định mệnh – giọng Trung Hoa audio-first.",
        "tone": "kịch tính, giàu nội tâm, cao trào dồn dập; tiết tấu cảnh rõ ràng",
        "style": "miêu tả âm thanh dày, đối thoại có nhịp nghỉ, từ vựng Á Đông (đừng tây hoá)",
        "world": "cổ đại giả tưởng với bang phái, gia tộc, bí cảnh, hệ thống nhiệm vụ",
        "tropes": ["hôn ước", "phản bội", "nợ máu", "tu luyện cấp bậc", "bí kíp/linh căn"],
        "taboos": ["siêu anh hùng kiểu Mỹ", "hài lố", "slang hiện đại quá mức"],
        "image_style": "donghua, nét Á Đông, ánh sáng filmic ấm, palette đỏ–vàng–đen",
        "sfx_style": "chiêng trống, tì bà, tiếng áo lụa, kiếm khí, ambience cổ trấn",
    },
    "Tu Tiên · Huyền Huyễn": {
        "tagline": "Tu đạo–nghịch thiên, đại giáo phái, bí cảnh sát phạt, thiên kiếp.",
        "tone": "sử thi, trang nghiêm, huyền bí",
        "style": "ngôn ngữ cổ phong, ẩn dụ thiên địa, pháp khí/linh lực",
        "world": "chư quốc, tiên môn, cảnh giới (Luyện khí→Trúc cơ→Kim đan→Nguyên anh→Hóa thần…)",
        "tropes": ["đại hội tranh tài", "bí cảnh di tích", "linh thú", "đan dược", "đạo lữ"],
        "taboos": ["hài lố hiện đại", "khoa học hiện đại giải thích phép"],
        "image_style": "núi non tiên cảnh, vân khí, y bào phiêu dật",
        "sfx_style": "chuông đồng, tiếng pháp trận, gió mây, sấm thiên kiếp",
    },
    "Cyberpunk · Hậu Tận Thế": {
        "tagline": "Đô thị neon, tập đoàn AI, sinh tồn sau sụp đổ.",
        "tone": "lạnh, chắc nhịp, noir",
        "style": "từ vựng công nghệ, xen thuật ngữ Việt hoá (không lạm dụng tiếng Anh)",
        "world": "megacity tầng lớp, mạng lưới thần kinh, implant, băng đảng",
        "tropes": ["nhiệm vụ đột nhập", "truy vết dữ liệu", "ảo giác mạng"],
        "taboos": ["steampunk lạc tông", "phép thuật Trung cổ"],
        "image_style": "neon rain, hạt mưa bokeh, góc máy thấp, hẻm ẩm ướt",
        "sfx_style": "dòng điện, hum máy chủ, mưa, tàu trên cao, radio chatter",
    },
    "Kinh Dị · Sinh Tồn": {
        "tagline": "Căn nhà cũ, nghi thức cấm, tín hiệu radio… sống còn.",
        "tone": "rón rén, căng dây, bùng nổ ngắn",
        "style": "miêu tả thính giác ưu tiên: tiếng thở, sàn gỗ, cửa kẽo kẹt",
        "world": "thị trấn heo hút, truyền thuyết địa phương, nghi thức cổ",
        "tropes": ["điều tra manh mối", "vật hiến tế", "bản đồ viết tay"],
        "taboos": ["máu me rẻ tiền", "giải thích tường tận phá sợ hãi"],
        "image_style": "low-key, hạt film, flare yếu, tông lạnh-xanh",
        "sfx_style": "floor creak, wind howl, radio static, sub-bass hit",
    },
    "Cổ Đại · Cung Đấu": {
        "tagline": "Tranh sủng – mưu quyền – thư phòng và ngọc tỷ.",
        "tone": "tinh tế, ẩn nhẫn, đòn tâm lý",
        "style": "điển cố, thơ phú, ẩn ý trong đối thoại",
        "world": "hoàng cung, lục bộ, phe phái, lễ nghi",
        "tropes": ["thưởng hoa", "tiệc yến", "mật chỉ", "án oan"],
        "taboos": ["đánh nhau lộ liễu, phản cung vô lý"],
        "image_style": "đèn lồng đỏ, lụa sa, bóng cửa hoa chạm",
        "sfx_style": "tỳ bà, guốc gỗ, rèm hạt châu, mực mài",
    },
    "Hiện Đại · Trinh Thám": {
        "tagline": "Án chuỗi, hiện trường lạnh, thủ pháp tâm lý.",
        "tone": "điềm tĩnh, logic, twist cuối",
        "style": "ngôn ngữ điều tra, thủ pháp pháp y vừa đủ",
        "world": "đội chuyên án, camera đô thị, dữ liệu viễn thông",
        "tropes": ["đối chất", "dựng lại hiện trường", "giờ chết giả"],
        "taboos": ["suy diễn siêu nhiên không căn cứ"],
        "image_style": "ánh đèn sodium, crime scene tape, bảng ghim ảnh chỉ đỏ",
        "sfx_style": "máy ảnh bấm, còi hụ xa, bước chân hành lang, bút dạ quang",
    },
    "Võ Hiệp · Giang Hồ": {
        "tagline": "Ân oán giang hồ, bí kíp thất truyền, tửu quán bão táp.",
        "tone": "hiệp nghĩa, bi tráng, phong vân biến ảo",
        "style": "chiêu thức có tên, thân pháp, nội lực",
        "world": "bang phái, lãnh địa, minh giáo – chính đạo",
        "tropes": ["tỷ võ", "tranh đoạt bí kíp", "huynh đệ tương tàn"],
        "taboos": ["siêu nhiên quá mức", "vũ khí tương lai"],
        "image_style": "cầu treo mù sương, áo choàng bay, chưởng lực gợn lá",
        "sfx_style": "tiếng kiếm rút, tay áo quét gió, trống trận, tiếng hồ tiêu",
    }
}

def preset_block(name: str) -> str:
    p = PRESETS.get(name, {})
    if not p: 
        return ""
    lines = ["[HỒ SƠ PRESET]"]
    for k in ["tagline","tone","style","world","tropes","taboos","image_style","sfx_style"]:
        v = p.get(k)
        if v is None: 
            continue
        if isinstance(v, (list, tuple)):
            vv = ", ".join(v)
        else:
            vv = str(v)
        lines.append(f"- {k}: {vv}")
    return "\n".join(lines)
