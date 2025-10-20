
# -*- coding: utf-8 -*-
"""
Centralized preset registry for Gemini Story Studio.
Each preset defines tone/style/world/tropes and audio-first hints
that will be injected into prompt builders.
"""
#    "Trung Quốc · Xuyên Không · Ngôn Tình · Hệ Thống": {
#         "tagline": "Xuyên không – báo thù – cặp đôi định mệnh – giọng Trung Hoa audio-first.",
#         "tone": "kịch tính, giàu nội tâm, cao trào dồn dập; tiết tấu cảnh rõ ràng",
#         "style": "miêu tả âm thanh dày, đối thoại có nhịp nghỉ, từ vựng Á Đông (đừng tây hoá)",
#         "world": "cổ đại giả tưởng với bang phái, gia tộc, bí cảnh, hệ thống nhiệm vụ",
#         "tropes": ["hôn ước", "phản bội", "nợ máu", "tu luyện cấp bậc", "bí kíp/linh căn"],
#         "taboos": ["siêu anh hùng kiểu Mỹ", "hài lố", "slang hiện đại quá mức"],
#         "image_style": "donghua, nét Á Đông, ánh sáng filmic ấm, palette đỏ–vàng–đen",
#         "sfx_style": "chiêng trống, tì bà, tiếng áo lụa, kiếm khí, ambience cổ trấn",
#     },
PRESETS = {
 
     "Trung Quốc": {
        "tagline": "Không khí Á Đông đậm nét, nghi lễ – gia tộc – môn phái.",
        "tone": "trang trọng, dày văn hoá, nhịp vừa – có cao trào khi cần",
        "style": "từ vựng cổ phong, ẩn dụ, phép xưng hô – tước vị chuẩn; tránh tây hoá",
        "world": "cổ đại giả tưởng: hoàng triều, gia tộc, bang phái, sơn xuyên, cổ trấn",
        "tropes": ["gia pháp – tông quy", "môn quy – lễ nghi", "án oan – mật chỉ"],
        "taboos": ["slang hiện đại", "siêu anh hùng kiểu Mỹ"],
        "image_style": "donghua, nét Á Đông, ánh đèn lồng ấm, palette đỏ–vàng–đen",
        "sfx_style": "tỳ bà, chiêng trống, tiếng áo lụa, guốc gỗ, ambience cổ trấn",
    },

    "Xuyên Không": {
        "tagline": "Linh hồn vượt thời – đổi thân phận – mở màn sốc văn minh.",
        "tone": "kịch tính mở đầu, kinh ngạc → thích nghi, nhịp tăng dần",
        "style": "mô tả sự lệch pha văn minh, độc thoại nội tâm sắc nét",
        "world": "thế giới đích: cổ/giả tưởng, bang phái, quy tắc khác lạ",
        "tropes": ["thân xác mới", "kiến thức hiện đại áp dụng cổ đại", "bảng nhiệm vụ đầu tiên"],
        "taboos": ["giải thích khoa học dông dài phá nhịp", "hài lố quá tay"],
        "image_style": "chuyển cảnh ánh sáng xoáy, viền sáng linh hồn, filmic ấm – lạnh tương phản",
        "sfx_style": "whoosh xuyên thời, nhịp tim, âm vọng xa, chime siêu thực",
    },

    "Ngôn Tình": {
        "tagline": "Cặp đôi định mệnh – hiểu lầm – cứu rỗi – hoá giải.",
        "tone": "giàu nội tâm, êm – bùng – lắng, chú trọng cảm xúc",
        "style": "đối thoại có nhịp nghỉ, ẩn ý – luyến tiếc – thổ lộ",
        "world": "gia tộc – triều chính – giang hồ tuỳ bối cảnh; trọng quan hệ",
        "tropes": ["hôn ước", "phản bội – tín nhiệm lại", "đồng sinh cộng tử", "gato nhẹ"],
        "taboos": ["hài lố", "slang hiện đại quá mức"],
        "image_style": "soft light, bloom nhẹ, close-up ánh mắt – bàn tay",
        "sfx_style": "tiếng thở, vải khẽ động, đàn tỳ bà/piano nhẹ, ambience đêm",
    },

    "Hệ Thống": {
        "tagline": "Giao diện nhiệm vụ – thăng cấp – thưởng phạt – build meta.",
        "tone": "rõ ràng, nhịp mạch nhiệm vụ, tăng độ thử thách",
        "style": "log hệ thống gọn; tooltip/thuộc tính; quyết định có hậu quả",
        "world": "bí cảnh – phụ bản – trial; tích điểm, bảng xếp hạng",
        "tropes": ["nhiệm vụ ẩn", "phần thưởng bất ngờ", "debuff/penalty", "build đa nhánh"],
        "taboos": ["spam thuật ngữ rối mắt", "đứt mạch cảm xúc vì bảng số"],
        "image_style": "HUD bán trong suốt, ánh viền lam, hạt light UI",
        "sfx_style": "UI blip, confirm ping, level-up chime, critical hit",
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
