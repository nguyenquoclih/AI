import pygame
import os
import random
import math
from pathfinding import Pathfinder

pygame.init()
print("Pygame initialized...")

WIDTH, HEIGHT = 1280, 720
FPS = 60
MAP_W, MAP_H = 4000, 20000

# Định nghĩa các tầng sinh học (Y range)
LAYERS = {
    "SPACE": (-5000, 0),
    "SURFACE": (1000, 4000), # Bắt đầu từ 1000 để tránh khoảng trống to ở trên cùng
    "UNDERGROUND": (4000, 8000),
    "INFECTED": (8000, 12000),
    "ORGANIC": (12000, 16000),
    "CORE": (16000, 20000)
}

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sinh Tồn: Khám Phá Rừng Sâu")
clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 20)
small_font = pygame.font.SysFont("consolas", 16)
title_font = pygame.font.SysFont("consolas", 36, bold=True)

# --- DIR AND ASSETS ---
ASSET_DIR = os.path.dirname(__file__)
GRAPHICS_DIR = os.path.join(ASSET_DIR, "Graphics")

def load_image(*parts):
    path = os.path.join(GRAPHICS_DIR, *parts)
    if not os.path.exists(path): return None
    try: return pygame.image.load(path).convert_alpha()
    except: return None

def slice_sheet(sheet, columns, rows):
    if not sheet: return []
    w = sheet.get_width() // columns
    h = sheet.get_height() // rows
    frames = []
    for r in range(rows):
        for c in range(columns):
            frames.append(sheet.subsurface(pygame.Rect(c*w, r*h, w, h)).copy())
    return frames

def trim_surface(surface):
    if not surface: return None
    bounds = surface.get_bounding_rect()
    if bounds.width <= 0 or bounds.height <= 0: return surface
    return surface.subsurface(bounds).copy()

def trim_animation(frames):
    if not frames: return []
    # Find the maximum bounding box across all frames to prevent jitter
    min_x, min_y, max_x, max_y = 9999, 9999, 0, 0
    for frame in frames:
        bounds = frame.get_bounding_rect()
        if bounds.width > 0 and bounds.height > 0:
            min_x = min(min_x, bounds.x)
            min_y = min(min_y, bounds.y)
            max_x = max(max_x, bounds.x + bounds.width)
            max_y = max(max_y, bounds.y + bounds.height)
            
    if max_x <= min_x or max_y <= min_y: return frames
    
    trimmed = []
    trim_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
    for frame in frames:
        trimmed.append(frame.subsurface(trim_rect).copy())
    return trimmed

SPRITES = {}

def load_sprites():
    # Warrior (Player 1)
    w_sheet = load_image("Main Character", "Warrior_Sheet-Effect.png")
    if w_sheet:
        w_frames = slice_sheet(w_sheet, 6, 17)
        SPRITES["warrior_idle"] = trim_animation(w_frames[0:6])
        SPRITES["warrior_walk"] = trim_animation(w_frames[6:12])
        SPRITES["warrior_attack"] = trim_animation(w_frames[18:24])
    
    # Red Hood (Player 2)
    r_sheet = load_image("Enemies", "Red Hood", "red hood itch free Copy-Sheet.png")
    if r_sheet:
        r_frames = slice_sheet(r_sheet, 12, 11)
        SPRITES["red_hood_idle"] = [pygame.transform.flip(f, True, False) for f in trim_animation(r_frames[0:12])]
        SPRITES["red_hood_walk"] = [pygame.transform.flip(f, True, False) for f in trim_animation(r_frames[12:24])]
        SPRITES["red_hood_attack"] = [pygame.transform.flip(f, True, False) for f in trim_animation(r_frames[72:84])]
        SPRITES["kẻ bò trườn"] = trim_animation(r_frames[0:4]) # Enemy usage
        
    # Skeleton (Player 3)
    s_idle = load_image("Enemies", "Skeleton", "Skeleton Idle.png")
    if s_idle: SPRITES["skeleton_idle"] = trim_animation(slice_sheet(s_idle, 11, 1))
    s_walk = load_image("Enemies", "Skeleton", "Skeleton Walk.png")
    if s_walk: SPRITES["skeleton_walk"] = trim_animation(slice_sheet(s_walk, 13, 1))
    s_atk = load_image("Enemies", "Skeleton", "Skeleton Attack.png")
    if s_atk: SPRITES["skeleton_attack"] = trim_animation(slice_sheet(s_atk, 18, 1))

    img = load_image("tau_xanh.png")
    if img: SPRITES["nerve_cruiser"] = img
    img = load_image("tau_do.png")
    if img: SPRITES["flesh_pod"] = img

    w_sheet = load_image("Main Character", "Warrior_Sheet-Effect.png")
    if w_sheet:
        w_frames = slice_sheet(w_sheet, 6, 17)
        SPRITES["player_idle"] = trim_animation(w_frames[0:6])
        SPRITES["player_walk"] = trim_animation(w_frames[6:12])
        SPRITES["player_attack"] = trim_animation(w_frames[18:24])
    
    TARGET_H = 33  # Bằng chiều cao warrior (đã đo: 33px)
    
    def scale_anim_to_h(raw_frames, target_h):
        """Trim toàn bộ animation với bbox nhất quán, rồi scale về đúng target_h"""
        trimmed = trim_animation(raw_frames)
        result = []
        for s in trimmed:
            h = s.get_height()
            if h == 0:
                result.append(s)
                continue
            w = max(1, int(s.get_width() * target_h / h))
            result.append(pygame.transform.scale(s, (w, target_h)))
        return result

    # Quái Vật Bóng Đêm
    nb_sheet = load_image("Enemies", "Night born", "NightBorne.png")
    if nb_sheet: 
        raw_idle = slice_sheet(nb_sheet, 23, 5)[0:9]
        raw_run = slice_sheet(nb_sheet, 23, 5)[23:29]
        raw_attack = slice_sheet(nb_sheet, 23, 5)[46:58]
        SPRITES["Quái Vật Bóng Đêm_idle"] = scale_anim_to_h(raw_idle, TARGET_H)
        SPRITES["Quái Vật Bóng Đêm_run"] = scale_anim_to_h(raw_run, TARGET_H)
        SPRITES["Quái Vật Bóng Đêm_attack"] = scale_anim_to_h(raw_attack, TARGET_H)
    
    # Slime Bùn (thay Red Hood)
    sl_sheet = load_image("Enemies", "Slime", "slime-Sheet.png")
    if sl_sheet:
        raw_idle = slice_sheet(sl_sheet, 4, 3)[0:4]    # Hàng 1: idle
        raw_run  = slice_sheet(sl_sheet, 4, 3)[4:8]    # Hàng 2: di chuyển
        raw_attack = slice_sheet(sl_sheet, 4, 3)[8:12] # Hàng 3: tấn công
        SPRITES["Slime_idle"] = scale_anim_to_h(raw_idle, TARGET_H)
        SPRITES["Slime_run"] = scale_anim_to_h(raw_run, TARGET_H)
        SPRITES["Slime_attack"] = scale_anim_to_h(raw_attack, TARGET_H)
    
    # Yêu Tinh Rừng
    bd_sheet = load_image("Enemies", "Briner of Death", "Bringer-of-Death-SpritSheet.png")
    if bd_sheet: 
        raw_idle = slice_sheet(bd_sheet, 8, 8)[0:8]
        raw_run = slice_sheet(bd_sheet, 8, 8)[8:16]
        raw_attack = slice_sheet(bd_sheet, 8, 8)[16:24]
        SPRITES["Yêu Tinh Rừng_idle"] = scale_anim_to_h(raw_idle, TARGET_H + 3)
        SPRITES["Yêu Tinh Rừng_run"] = scale_anim_to_h(raw_run, TARGET_H + 3)
        SPRITES["Yêu Tinh Rừng_attack"] = scale_anim_to_h(raw_attack, TARGET_H + 3)
        
    icon_sheet = load_image("Icons", "#2 - Transparent Icons & Drop Shadow.png")
    if icon_sheet:
        def ic(col, row): return icon_sheet.subsurface(pygame.Rect(col*32, row*32, 32, 32)).copy()
        SPRITES["wood"]   = ic(0, 8)
        SPRITES["stone"]  = ic(0, 14)
        SPRITES["meat"]   = ic(0, 12)
        SPRITES["hide"]   = ic(3, 3)
        SPRITES["water"]  = ic(0, 15)
        SPRITES["bẫy thú"]        = ic(8, 1)
        SPRITES["lửa trại"]   = ic(1, 4)
        # Vũ khí icons
        SPRITES["icon_dao_gam"]         = ic(0, 5)   # kiếm ngắn
        SPRITES["icon_kiem_go"]         = ic(1, 5)   # kiếm dài
        SPRITES["icon_kiem_cuong_hoa"]  = ic(4, 5)   # kiếm đôi
        # Giáp icons
        SPRITES["icon_ao_choang_la"]    = ic(5, 7)  # áo giáp xanh
        SPRITES["icon_giap_da"]         = ic(4, 7)  # áo giáp đậm
        SPRITES["icon_bua_rung_sau"]    = ic(3, 7)  # giáp nâu
        # Bảo hộ icons
        SPRITES["icon_mat_na_phong_doc"]= ic(0, 7)  # mũ bảo hộ xanh
        SPRITES["icon_bua_ho_menh"]      = ic(1, 7)  # giáp ngực tối
        SPRITES["icon_thao_duoc_giai_doc"] = ic(2, 7)  # giáp đặc biệt
        SPRITES["icon_giap_co_dai"]      = ic(0, 6)  # khiên
        SPRITES["icon_torch"]            = ic(2, 4)  # Đuốc (giả lập vị trí)
        # Balo / vật phẩm
        SPRITES["icon_backpack"]  = ic(10, 7)  # balo tím
        SPRITES["icon_shield"]    = ic(0, 6)   # khiên tròn
        SPRITES["icon_potion"]    = ic(0, 9)   # thuốc đỏ
        SPRITES["icon_nam_linh_chi"] = ic(6, 9)   # bình xanh
        SPRITES["icon_duoc_thao"]    = ic(3, 9)   # bình vàng
        SPRITES["icon_thit_thu"]     = ic(0, 12)  # thịt
        SPRITES["icon_go_soi"]       = ic(8, 8)   # gỗ/sợi
        SPRITES["icon_nhua_cay_doc"] = ic(5, 9) # thuốc tím
        SPRITES["icon_da_thu"]       = ic(9, 8) # kính lúp
        SPRITES["icon_nuoc_suoi"]    = ic(2, 0) # giọt nước


    # Environment
    bg1 = load_image("Surroundings", "Forest_Bg", "background_layer_1.png")
    bg2 = load_image("Surroundings", "Forest_Bg", "background_layer_2.png")
    bg3 = load_image("Surroundings", "Forest_Bg", "background_layer_3.png")
    if bg1: SPRITES["bg1"] = bg1
    if bg2: SPRITES["bg2"] = bg2
    if bg3: SPRITES["bg3"] = bg3
    

    
    SPRITES["tree"] = load_image("Surroundings", "Valley_Decor", "sign.png")
    SPRITES["rock"] = load_image("Surroundings", "Valley_Decor", "rock_1.png")
    SPRITES["grass_1"] = load_image("Surroundings", "Valley_Decor", "grass_1.png")
    SPRITES["grass_2"] = load_image("Surroundings", "Valley_Decor", "grass_2.png")
    SPRITES["rock_2"] = load_image("Surroundings", "Valley_Decor", "rock_2.png")
    SPRITES["fence_1"] = load_image("Surroundings", "Valley_Decor", "fence_1.png")
    SPRITES["lamp"] = load_image("Surroundings", "Valley_Decor", "lamp.png")

    # Items tu collection
    for name in ["thit_thu", "go_soi", "cay", "ho_nuoc", "da_thu"]:
        item_img = load_image("Items", f"{name}.png")
        if item_img: SPRITES[f"item_{name}"] = item_img

    # Space assets (CLEANED - Only Planets and Black Hole)
    for name in ["planet_earth", "planet_lava", "planet_grey", "planet_ice", "black_hole"]:
        space_img = load_image("Space", f"{name}.png")
        if space_img: SPRITES[f"space_{name}"] = space_img

load_sprites()


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def check_wall(pos, radius=0):
    try: map_data
    except NameError: return False
    
    # Kiểm tra 4 góc của bounding box quanh vật thể
    points = [
        (pos[0] - radius, pos[1] - radius),
        (pos[0] + radius, pos[1] - radius),
        (pos[0] - radius, pos[1] + radius),
        (pos[0] + radius, pos[1] + radius)
    ]
    for px, py in points:
        col = int(px // TILE_SIZE)
        row = int(py // TILE_SIZE)
        if 0 <= row < len(map_data) and 0 <= col < len(map_data[0]):
            if map_data[row][col] == 1:
                return True
                
    # Kiem tra va cham voi cay coi
    try: resources
    except NameError: return False
    
    for r in resources:
        if r.kind == "cây sồi non":
            # Goc cay co ban kinh va cham khoang 20
            if distance(pos, r.pos) < radius + 20:
                return True
                
    return False


def get_bg_color(y):
    # Mau nen theo khu vuc rung
    # Darken based on depth factor
    depth_factor = max(0.1, 1.0 - (y / MAP_H) * 0.8)
    
    def darken(col, f):
        return (int(col[0] * f), int(col[1] * f), int(col[2] * f))

    if y < LAYERS["SURFACE"][1]: return darken((30, 80, 40), depth_factor)      # Bia rung (Xanh la)
    if y < LAYERS["UNDERGROUND"][1]: return darken((20, 50, 30), depth_factor)  # Rung gia (Xanh dam)
    if y < LAYERS["INFECTED"][1]: return darken((50, 40, 70), depth_factor)     # Dam lay (Tim sam)
    if y < LAYERS["ORGANIC"][1]: return darken((40, 60, 60), depth_factor)      # Thung lung (Xanh xam)
    return darken((20, 20, 30), depth_factor)                                   # Loi rung (Den xanh)

def get_biome_name(y):
    if y < LAYERS["SURFACE"][1]: return "BÌA RỪNG"
    if y < LAYERS["UNDERGROUND"][1]: return "RỪNG GIÀ"
    if y < LAYERS["INFECTED"][1]: return "ĐẦM LẦY ĐỘC"
    if y < LAYERS["ORGANIC"][1]: return "THUNG LŨNG SƯƠNG MÙ"
    return "LÕI RỪNG CỔ ĐẠI"

def draw_bar(surface, x, y, w, h, current, max_val, color, label=""):
    ratio = max(0, min(1, current / max_val if max_val > 0 else 0))
    # Outer glow/border
    pygame.draw.rect(surface, (20, 20, 20), (x-2, y-2, w+4, h+4), border_radius=4)
    # Background
    bg_col = (int(color[0]*0.3), int(color[1]*0.3), int(color[2]*0.3))
    pygame.draw.rect(surface, bg_col, (x, y, w, h), border_radius=3)
    # Foreground bar
    if ratio > 0:
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h), border_radius=3)
        # Highlight top of the bar
        highlight_col = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))
        pygame.draw.rect(surface, highlight_col, (x, y, int(w * ratio), h // 3), border_radius=2)
    # Inner border
    pygame.draw.rect(surface, (180, 180, 180), (x, y, w, h), 1, border_radius=3)
    
    # In chữ vào giữa thanh
    if label:
        # Nếu font chưa load kịp thì bỏ qua, nhưng thường thì có sẵn font ở file scope
        txt = small_font.render(f"{label}: {int(current)}/{int(max_val)}", True, (255, 255, 255))
        # Tạo viền đen cho chữ dễ đọc
        outline = small_font.render(f"{label}: {int(current)}/{int(max_val)}", True, (0, 0, 0))
        cx, cy = x + w//2 - txt.get_width()//2, y + h//2 - txt.get_height()//2
        surface.blit(outline, (cx+1, cy+1))
        surface.blit(txt, (cx, cy))


class Camera:
    def __init__(self):
        self.x = 0; self.y = 0
        self.zoom = 1.0 # Trả về 1.0 để ổn định tọa độ trước
    
    def apply(self, pos):
        # Tọa độ tương đối so với Camera
        return (int((pos[0] - self.x)), int((pos[1] - self.y)))

    def update(self, target_pos):
        # Giữ nhân vật luôn ở giữa
        self.x = target_pos[0] - WIDTH // 2
        self.y = target_pos[1] - HEIGHT // 2

class Player:
    def __init__(self, char_type="warrior"):
        self.char_type = char_type
        self.pos = [MAP_W//2, 500] # Bắt đầu tại Bề mặt (Surface)
        self.radius = 16
        
        # Chỉ số cơ bản
        self.max_hunger = 100.0; self.hunger = self.max_hunger
        self.max_thirst = 100.0; self.thirst = self.max_thirst
        self.max_sanity = 100.0; self.sanity = self.max_sanity
        self.max_stamina = 500.0
        self.base_damage = 20
        self.speed = 250
        self.max_hp = 250.0
        
        # Chỉ số riêng cho từng nhân vật
        if self.char_type == "warrior":
            self.max_hp = 250.0
            self.speed = 250
            self.base_damage = 25
        elif self.char_type == "red_hood":
            self.max_hp = 200.0
            self.speed = 320         # Chạy rất nhanh
            self.max_stamina = 600.0 # Thể lực cao để né đòn
            self.base_damage = 15
        elif self.char_type == "skeleton":
            self.max_hp = 180.0
            self.speed = 200         # Đi chậm
            self.base_damage = 40    # Sát thương phép/cơ bản cực cao
            
        self.hp = self.max_hp
        self.stamina = self.max_stamina
        
        self.facing_left = False
        self.state = "idle"
        self.frame = 0.0
        self.inventory = {
            "thịt thú": 0, "nấm linh chi": 0, "gỗ sồi": 0, "nước suối": 0,
            "dược thảo": 0, "nhựa cây độc": 0, "da thú giáp": 0,
            "lửa trại": 0, "bẫy thú": 0,
            "dao găm": 0, "kiếm gỗ": 0, "vũ khí cường hóa": 0,
            "áo choàng lá": 0, "giáp da": 0, "bùa rừng sâu": 0,
            "mặt nạ phòng độc": 0, "bùa hộ mệnh": 0, "thảo dược giải độc": 0, "giáp cổ đại": 0
        }
        self.attack_cd = 0
        self.vision_radius = 400
        
        # Auto play attributes
        self.auto_play = False
        self.auto_path = []
        self.auto_timer = 0
        self.simulated_key_f = False
        self.simulated_key_e = False
        self.simulated_key_q = False
        self.simulated_key_w = False

    def get_damage(self):
        # Lấy sát thương của vũ khí MẠNH NHẤT trong túi đồ, không cộng dồn
        weapon_bonus = 0
        if self.inventory.get("vũ khí cường hóa", 0) > 0:
            weapon_bonus = 70
        elif self.inventory.get("kiếm gỗ", 0) > 0:
            weapon_bonus = 40
        elif self.inventory.get("dao găm", 0) > 0:
            weapon_bonus = 25
            
        # Thêm sát thương từ DNA nếu có
        dna_bonus = 10 if global_genes.get('start_sword') else 0
        return self.base_damage + weapon_bonus + dna_bonus

    def can_craft(self, item):
        if item not in RECIPES: return False
        for k, v in RECIPES[item].items():
            if self.inventory.get(k, 0) < v: return False
        return True

    def run_auto_logic(self, dt, animals, resources, drops, landed_ship_pos):
        self.auto_timer -= dt
        
        # Tự động ăn uống sinh tồn (Ăn khi đói hoặc khi MÁU THẤP)
        if (self.hunger < 40 or self.hp < self.max_hp * 0.6) and self.inventory.get("thịt thú", 0) > 0: 
            self.simulated_key_q = True
        else: 
            self.simulated_key_q = False
        
        if self.thirst < 40 and self.inventory.get("nước suối", 0) > 0: self.simulated_key_w = True
        else: self.simulated_key_w = False

        self.simulated_key_f = False
        self.simulated_key_e = False
        self.simulated_key_p = False
        
        current_time = pygame.time.get_ticks()
        if current_time - getattr(self, "last_craft_time", 0) > 2000:
            self.last_craft_time = current_time
            if not hasattr(self, "simulated_craft_requests"): self.simulated_craft_requests = []
            craft_targets = ["dao găm", "kiếm gỗ", "vũ khí cường hóa", 
                             "áo choàng lá", "giáp da", "bùa rừng sâu",
                             "mặt nạ phòng độc", "bùa hộ mệnh", "thảo dược giải độc", "giáp cổ đại"]
            for target in craft_targets:
                if self.inventory.get(target, 0) == 0 and self.can_craft(target):
                    self.simulated_craft_requests.append(target)
                    break

        if self.auto_timer <= 0:
            self.auto_timer = 0.5
            start_node = (int(self.pos[0] // 64), int(self.pos[1] // 64))
            target_pos = None
            
            # 1. KITE & SURVIVAL: Nếu máu quá thấp (<30%), CHẠY TRỐN
            is_fleeing = False
            if self.hp < self.max_hp * 0.3:
                for a in animals:
                    if distance(self.pos, a.pos) < 250:
                        nx = self.pos[0] + (self.pos[0] - a.pos[0])
                        ny = self.pos[1] + (self.pos[1] - a.pos[1])
                        nx = max(100, min(MAP_W - 100, nx))
                        ny = max(100, min(MAP_H - 100, ny))
                        target_pos = [nx, ny]
                        is_fleeing = True
                        break
            
            self.is_fleeing = is_fleeing
            
            # 2. Sinh tồn khẩn cấp
            if not is_fleeing and self.hp < self.max_hp * 0.5 and self.inventory.get("thịt thú", 0) == 0:
                closest = 999999
                for d in drops:
                    if d.kind == "thịt thú" and distance(self.pos, d.pos) < closest:
                        closest = distance(self.pos, d.pos); target_pos = d.pos
                if not target_pos:
                    for a in animals:
                        if distance(self.pos, a.pos) < closest:
                            closest = distance(self.pos, a.pos); target_pos = a.pos
            elif not is_fleeing and self.thirst < 30 and self.inventory.get("nước suối", 0) == 0:
                closest = 999999
                for r in resources:
                    if r.kind == "suối nước" and distance(self.pos, r.pos) < closest:
                        closest = distance(self.pos, r.pos); target_pos = r.pos
            
            # 3. Ưu tiên Farm tài nguyên thiết yếu
            if not is_fleeing and not target_pos and self.inventory.get("gỗ sồi", 0) < 25:
                closest = 999999
                for r in resources:
                    if r.kind == "cây sồi non" and distance(self.pos, r.pos) < closest:
                        closest = distance(self.pos, r.pos); target_pos = r.pos

            if not is_fleeing and not target_pos and self.inventory.get("nước suối", 0) < 15:
                closest = 999999
                for r in resources:
                    if r.kind == "suối nước" and distance(self.pos, r.pos) < closest:
                        closest = distance(self.pos, r.pos); target_pos = r.pos

            # 4. Thực hiện quest / Phá đảo
            if not is_fleeing and not target_pos:
                if not ship_repaired:
                    # Tự động farm đúng đồ sửa tàu
                    inv = self.inventory
                    if inv.get("nấm linh chi", 0) < 10:
                        closest = 999999
                        for a in animals:
                            if a.kind == "Slime Bùn Bùn" and distance(self.pos, a.pos) < closest:
                                closest = distance(self.pos, a.pos); target_pos = a.pos
                    elif inv.get("dược thảo", 0) < 10 or inv.get("da thú giáp", 0) < 5:
                        closest = 999999
                        for a in animals:
                            if a.kind == "Yêu Tinh Rừng" and distance(self.pos, a.pos) < closest:
                                closest = distance(self.pos, a.pos); target_pos = a.pos
                    elif inv.get("nhựa cây độc", 0) < 5:
                        closest = 999999
                        for a in animals:
                            if a.kind in ["Yêu Tinh Rừng", "Quái Vật Bóng Đêm"] and distance(self.pos, a.pos) < closest:
                                closest = distance(self.pos, a.pos); target_pos = a.pos
                    else:
                        # Đã đủ nguyên liệu sửa tàu
                        target_pos = landed_ship_pos
                        if distance(self.pos, landed_ship_pos) < 150:
                            self.simulated_key_p = True
                else:
                    # Cày mặt nạ phòng độc trước tiên nếu chưa có
                    gear_needs = []
                    inv = self.inventory
                    
                    if not inv.get("mặt nạ phòng độc", 0) and not inv.get("bùa hộ mệnh", 0):
                        if inv.get("gỗ sồi", 0) < 10: gear_needs.append("cây sồi non")
                        if inv.get("nấm linh chi", 0) < 8: gear_needs.append("Slime Bùn Bùn")
                        if inv.get("dược thảo", 0) < 5: gear_needs.append("Yêu Tinh Rừng")
                    elif quest_system.tier >= 3 and not inv.get("bùa hộ mệnh", 0):
                        if inv.get("dược thảo", 0) < 15 or inv.get("da thú giáp", 0) < 10: gear_needs.append("Yêu Tinh Rừng")
                        if inv.get("thịt thú", 0) < 10: gear_needs.append("Slime Bùn Bùn")
                    elif quest_system.tier >= 4 and not inv.get("thảo dược giải độc", 0):
                        if inv.get("nước suối", 0) < 12: gear_needs.append("suối nước")
                        if inv.get("da thú giáp", 0) < 12 or inv.get("dược thảo", 0) < 8: gear_needs.append("Yêu Tinh Rừng")
                    elif quest_system.tier >= 5 and not inv.get("giáp cổ đại", 0):
                        if inv.get("nhựa cây độc", 0) < 20: gear_needs.append("Quái Vật Bóng Đêm")
                        if inv.get("da thú giáp", 0) < 20 or inv.get("dược thảo", 0) < 15: gear_needs.append("Yêu Tinh Rừng")
                    
                    if gear_needs:
                        closest = 999999
                        for a in animals:
                            if a.kind in gear_needs and distance(self.pos, a.pos) < closest:
                                closest = distance(self.pos, a.pos); target_pos = a.pos
                        if not target_pos:
                            for r in resources:
                                if r.kind in gear_needs and distance(self.pos, r.pos) < closest:
                                    closest = distance(self.pos, r.pos); target_pos = r.pos

                    # Cày vũ khí nếu chưa có
                    if not target_pos:
                        if not inv.get("kiếm gỗ", 0) and not inv.get("vũ khí cường hóa", 0):
                            wpn_needs = []
                            if inv.get("gỗ sồi", 0) < 10: wpn_needs.append("cây sồi non")
                            if inv.get("dược thảo", 0) < 5: wpn_needs.append("Yêu Tinh Rừng")
                            if inv.get("thịt thú", 0) < 5: wpn_needs.append("Slime Bùn Bùn")
                            if wpn_needs:
                                closest = 999999
                                for a in animals:
                                    if a.kind in wpn_needs and distance(self.pos, a.pos) < closest:
                                        closest = distance(self.pos, a.pos); target_pos = a.pos
                                if not target_pos:
                                    for r in resources:
                                        if r.kind in wpn_needs and distance(self.pos, r.pos) < closest:
                                            closest = distance(self.pos, r.pos); target_pos = r.pos

                    # Làm nhiệm vụ nếu không cần farm đồ
                    if not target_pos:
                        if quest_system.tier == 1:
                            closest = 999999
                            for a in animals:
                                if a.kind == "Slime Bùn Bùn" and distance(self.pos, a.pos) < closest:
                                    closest = distance(self.pos, a.pos); target_pos = a.pos
                        elif quest_system.tier == 2:
                            closest = 999999
                            for d in drops:
                                if d.kind == "thịt thú" and distance(self.pos, d.pos) < closest:
                                    closest = distance(self.pos, d.pos); target_pos = d.pos
                            if not target_pos:
                                for a in animals:
                                    if distance(self.pos, a.pos) < closest:
                                        closest = distance(self.pos, a.pos); target_pos = a.pos
                        elif quest_system.tier in [3, 4, 5]:
                            # Tiến dần xuống đáy (16000m)
                            found_empty = False
                            for dy_check in range(15, 30):
                                ny = start_node[1] + dy_check
                                for dx_check in range(-5, 6):
                                    nx = start_node[0] + dx_check
                                    if 0 <= nx < pathfinder.cols and 0 <= ny < pathfinder.rows:
                                        if pathfinder.map_data[ny][nx] == 0:
                                            target_pos = [nx * 64 + 32, ny * 64 + 32]
                                            found_empty = True
                                            break
                                if found_empty: break

            # Nếu xung quanh hoàn toàn trống, đi lang thang ngẫu nhiên
            if not target_pos:
                found_empty = False
                for _ in range(30):
                    nx = start_node[0] + random.randint(-20, 20)
                    ny = start_node[1] + random.randint(-5, 10)
                    if 0 <= nx < pathfinder.cols and 0 <= ny < pathfinder.rows:
                        if pathfinder.map_data[ny][nx] == 0:
                            target_pos = [nx * 64 + 32, ny * 64 + 32]
                            found_empty = True
                            break
            
            self.auto_target_pos = target_pos
            
            if target_pos:
                goal_node = (int(target_pos[0] // 64), int(target_pos[1] // 64))
                try:
                    if 0 <= start_node[0] < pathfinder.cols and 0 <= start_node[1] < pathfinder.rows and \
                       0 <= goal_node[0] < pathfinder.cols and 0 <= goal_node[1] < pathfinder.rows:
                        self.auto_path = pathfinder.a_star(start_node, goal_node, max_steps=600)
                except Exception:
                    self.auto_path = []

        dx, dy = 0, 0
        target_pos = getattr(self, "auto_target_pos", None)
        
        is_animal_target = False
        if target_pos:
            for a in animals:
                if a.pos == target_pos:
                    is_animal_target = True
                    break

        # Tương tác và tự vệ (Không bị chặn bởi kiting)
        enemy_nearby = False
        if not getattr(self, "is_fleeing", False):
            for a in animals:
                if distance(self.pos, a.pos) < 110:
                    enemy_nearby = True
                    break
                    
        if target_pos:
            if enemy_nearby or (is_animal_target and distance(self.pos, target_pos) < 110):
                self.simulated_key_f = True
            
            if not is_animal_target and distance(self.pos, target_pos) < 60:
                self.simulated_key_e = True
        elif enemy_nearby:
            self.simulated_key_f = True

        # Logic đánh Hit and Run: Né quái khi attack cooldown
        is_kiting = False
        if target_pos and self.attack_cd > 0:
            for a in animals:
                if distance(self.pos, a.pos) < 70:
                    dx, dy = self.pos[0] - a.pos[0], self.pos[1] - a.pos[1]
                    # Cho phép trượt tường, không set dx, dy = 0, 0
                    is_kiting = True
                    break

        if not is_kiting:
            # Ưu tiên đi theo A* để không bị đâm xuyên tường
            if self.auto_path and len(self.auto_path) > 0:
                target_node = self.auto_path[0]
                target_x = target_node[0] * 64 + 32
                target_y = target_node[1] * 64 + 32
                dx, dy = target_x - self.pos[0], target_y - self.pos[1]
                if math.hypot(dx, dy) < 30:
                    self.auto_path.pop(0)
            elif target_pos:
                # Nếu không có path, bay thẳng (bỏ giới hạn < 150 để tránh kẹt vĩnh viễn)
                dx, dy = target_pos[0] - self.pos[0], target_pos[1] - self.pos[1]

        l = math.hypot(dx, dy)
        if l > 0:
            dx, dy = dx/l, dy/l
            if dx < 0: self.facing_left = True
            elif dx > 0: self.facing_left = False
            
        # Nghỉ ngơi nếu thể lực cạn và đang ở khoảng cách an toàn
        if self.stamina < 50 and not is_kiting and not getattr(self, "is_fleeing", False):
            safe = True
            for a in animals:
                if distance(self.pos, a.pos) < 300:
                    safe = False
                    break
            if safe:
                return 0, 0, False
                
        running = l > 0 and (is_kiting or getattr(self, "is_fleeing", False)) and self.stamina > 0
        return dx, dy, running

    def update(self, dt, keys, animals=[], resources=[], drops=[], landed_ship_pos=None):
        dx, dy = 0, 0
        running = False
        if not getattr(self, "auto_play", False):
            if keys[pygame.K_UP]: dy -= 1
            if keys[pygame.K_DOWN]: dy += 1
            if keys[pygame.K_LEFT]: dx -= 1; self.facing_left = True
            if keys[pygame.K_RIGHT]: dx += 1; self.facing_left = False
            running = keys[pygame.K_LSHIFT] and self.stamina > 0
        else:
            dx, dy, running = self.run_auto_logic(dt, animals, resources, drops, landed_ship_pos)
            
        current_speed = self.speed * (1.5 if running else 1.0)
        
        if self.attack_cd > 0:
            self.state = "attack"
            self.attack_cd -= dt
        elif dx != 0 or dy != 0:
            self.state = "walk"
        else:
            self.state = "idle"
            
        self.frame += dt * 10
        
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            new_x = self.pos[0] + (dx / length) * current_speed * dt
            new_y = self.pos[1] + (dy / length) * current_speed * dt
            
            # Di chuyển rẽ nhánh theo X và Y để trượt dọc theo tường
            if not check_wall([new_x, self.pos[1]], self.radius * 0.8):
                self.pos[0] = new_x
            if not check_wall([self.pos[0], new_y], self.radius * 0.8):
                self.pos[1] = new_y
                
            if running: 
                self.stamina -= 30 * dt
            else:
                self.stamina += 15 * dt
        else:
            self.stamina += 40 * dt
            
        self.stamina = max(0, min(self.max_stamina, self.stamina))
        self.pos[0] = max(self.radius, min(MAP_W - self.radius, self.pos[0]))
        self.pos[1] = max(self.radius, min(MAP_H - self.radius, self.pos[1]))
        
        # Hunger/Thirst drain reduced if tier 4 completed
        drain_mult = 0.5 if quest_system.tier > 4 else 1.0
        self.hunger -= 1.0 * dt * drain_mult
        self.thirst -= 1.5 * dt * drain_mult
        
        if self.hunger <= 0 or self.thirst <= 0:
            self.hp -= 2.0 * dt
            
        self.hunger = max(0, min(self.max_hunger, self.hunger))
        self.thirst = max(0, min(self.max_thirst, self.thirst))
        self.sanity = max(0, min(self.max_sanity, self.sanity))

    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        pygame.draw.ellipse(surface, (0, 0, 0, 100), (x - 16, y + 8, 32, 12))
        
        anim_key = f"{self.char_type}_{self.state}"
        if anim_key in SPRITES and SPRITES[anim_key] and len(SPRITES[anim_key]) > 0:
            frames = SPRITES[anim_key]
            sprite = frames[int(self.frame) % len(frames)]
            if sprite:
                sprite = pygame.transform.flip(sprite, self.facing_left, False)
                surface.blit(sprite, (x - sprite.get_width()//2, y - sprite.get_height() + 10))
        else:
            pygame.draw.circle(surface, (80, 180, 100), (x, y), self.radius)

class Animal:
    def __init__(self, kind, y_range=(100, 3000)):
        # Tìm vị trí hợp lệ (không phải tường)
        px, py = random.randint(100, MAP_W-100), random.randint(y_range[0], y_range[1])
        for _ in range(50):
            tx, ty = random.randint(100, MAP_W-100), random.randint(y_range[0], y_range[1])
            col, row = int(tx // 64), int(ty // 64)
            if 0 <= row < len(map_data) and 0 <= col < len(map_data[0]):
                if map_data[row][col] == 0:
                    px, py = tx, ty
                    break
        self.pos = [px, py]
        self.kind = kind
        self.state = "wander"
        self.timer = 0
        self.frame = random.uniform(0, 10)
        self.direction = [random.uniform(-1,1), random.uniform(-1,1)]
        
        # Tiến hóa dựa trên Planet Awareness
        evolution_multiplier = 1.0 + (planet_awareness / 100.0)
        
        if kind == "Slime Bùn Bùn": self.hp = 20 * evolution_multiplier; self.speed = 45 * evolution_multiplier; self.radius = 12
        elif kind == "Yêu Tinh Rừng": self.hp = 50 * evolution_multiplier; self.speed = 90 * evolution_multiplier; self.radius = 20
        elif kind == "Quái Vật Bóng Đêm": self.hp = 70 * evolution_multiplier; self.speed = 120 * evolution_multiplier; self.radius = 18
        
        self.max_hp = self.hp
        # Armor plating mutation if player killed many
        self.armored = False
        if quest_system and quest_system.stats[kind] > 10:
            self.armored = True
            self.hp *= 1.5
            self.max_hp = self.hp
            
        self.path = []
        self.path_timer = 0

    def update(self, dt, player):
        self.frame += dt * 12 # Tăng tốc độ hoạt ảnh để mượt hơn
        dist_to_player = distance(self.pos, player.pos)
        self.timer -= dt
        
        # Nếu đang trong hoạt ảnh tấn công, không di chuyển
        if self.state == "attack":
            frames = SPRITES.get(self.kind + "_attack", [])
            if int(self.frame) >= len(frames):
                self.state = "chase"
                self.frame = 0
            return

        # AI Logic cho từng loại quái
        if self.kind == "Slime Bùn Bùn":
            self.anim_key = "Slime_run" if self.state == "chase" else "Slime_idle"
            if dist_to_player < 250:
                self.state = "chase"
                if dist_to_player < 35 and self.timer <= 0:
                    self.state = "attack"; self.frame = 0; self.anim_key = "Slime_attack"
                    player.hp -= 6
                    self.timer = 1.5
            elif self.timer <= 0:
                self.state = "wander"; self.timer = random.uniform(1, 3)
                self.direction = [random.uniform(-1,1), random.uniform(-1,1)]
                self.path = []

        elif self.kind == "Yêu Tinh Rừng":
            self.anim_key = "Yêu Tinh Rừng_run" if self.state == "chase" else "Yêu Tinh Rừng_idle"
            if dist_to_player < 400:
                self.state = "chase"
                if dist_to_player < 50 and self.timer <= 0:
                    self.state = "attack"; self.frame = 0; self.anim_key = "Yêu Tinh Rừng_attack"
                    player.hp -= 15
                    self.timer = 1.8
            elif self.timer <= 0:
                self.state = "wander"; self.timer = random.uniform(2, 4)
                self.direction = [random.uniform(-1,1), random.uniform(-1,1)]
                self.path = []

        elif self.kind == "Quái Vật Bóng Đêm":
            self.anim_key = "Quái Vật Bóng Đêm_run" if self.state == "chase" else "Quái Vật Bóng Đêm_idle"
            if dist_to_player < 550:
                self.state = "chase"
                if dist_to_player < 50 and self.timer <= 0:
                    self.state = "attack"; self.frame = 0; self.anim_key = "Quái Vật Bóng Đêm_attack"
                    player.hp -= 25
                    self.timer = 1.0
            elif self.timer <= 0:
                self.state = "wander"; self.timer = random.uniform(1, 2)
                self.direction = [random.uniform(-1,1), random.uniform(-1,1)]
                self.path = []

        self.path_timer -= dt
        if self.state == "chase":
            if self.path_timer <= 0:
                self.path_timer = random.uniform(0.5, 1.0)
                start_node = (int(self.pos[0] // 64), int(self.pos[1] // 64))
                goal_node = (int(player.pos[0] // 64), int(player.pos[1] // 64))
                
                try:
                    if 0 <= start_node[0] < pathfinder.cols and 0 <= start_node[1] < pathfinder.rows and \
                       0 <= goal_node[0] < pathfinder.cols and 0 <= goal_node[1] < pathfinder.rows:
                        if self.kind == "Slime Bùn Bùn":
                            self.path = pathfinder.bfs(start_node, goal_node, max_steps=100)
                        elif self.kind == "Yêu Tinh Rừng":
                            self.path = pathfinder.dfs(start_node, goal_node, max_steps=150)
                        elif self.kind == "Quái Vật Bóng Đêm":
                            self.path = pathfinder.a_star(start_node, goal_node, max_steps=300)
                except Exception:
                    self.path = []

            if self.path and len(self.path) > 0:
                target_node = self.path[0]
                target_x = target_node[0] * 64 + 32
                target_y = target_node[1] * 64 + 32
                dx, dy = target_x - self.pos[0], target_y - self.pos[1]
                dist_to_node = math.hypot(dx, dy)
                
                if dist_to_node < 20:
                    self.path.pop(0)
                    if not self.path:
                        dx, dy = player.pos[0] - self.pos[0], player.pos[1] - self.pos[1]
                
                l = math.hypot(dx, dy)
                if l > 0:
                    self.direction = [dx/l, dy/l]
            else:
                dx, dy = player.pos[0] - self.pos[0], player.pos[1] - self.pos[1]
                l = math.hypot(dx, dy)
                if l > 0:
                    self.direction = [dx/l, dy/l]

        l = math.hypot(self.direction[0], self.direction[1])
        if l > 0:
            new_x = self.pos[0] + (self.direction[0]/l) * self.speed * dt
            new_y = self.pos[1] + (self.direction[1]/l) * self.speed * dt
            
            # Quái vật cũng không được đi xuyên tường
            if not check_wall([new_x, self.pos[1]], self.radius * 0.8):
                self.pos[0] = new_x
            else:
                self.direction[0] *= -1 # Đụng tường dội lại
                
            if not check_wall([self.pos[0], new_y], self.radius * 0.8):
                self.pos[1] = new_y
            else:
                self.direction[1] *= -1
        self.pos[0] = max(self.radius, min(MAP_W - self.radius, self.pos[0]))
        self.pos[1] = max(self.radius, min(MAP_H - self.radius, self.pos[1]))

    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        
        anim_key = getattr(self, "anim_key", self.kind + "_idle")
        if anim_key in SPRITES and SPRITES[anim_key]:
            frames = SPRITES[anim_key]
            sprite = frames[int(self.frame) % len(frames)]
            if sprite:
                # Lật hình theo hướng di chuyển
                if self.direction[0] < 0:
                    sprite = pygame.transform.flip(sprite, True, False)
                
                sw, sh = sprite.get_width(), sprite.get_height()
                
                # Vẽ bóng dựa trên kích thước thực tế của sprite đã cắt
                pygame.draw.ellipse(surface, (0, 0, 0, 70), (x - sw//4, y - 5, sw//2, 10))
                
                # Vẽ quái vật (y là mặt đất)
                surface.blit(sprite, (x - sw//2, y - sh))
                
                # === HP BAR phía trên quái vật ===
                bar_w = max(sw, 30)
                bar_x = x - bar_w // 2
                bar_y = y - sh - 8
                hp_ratio = max(0, self.hp / self.max_hp)
                pygame.draw.rect(surface, (60, 0, 0), (bar_x, bar_y, bar_w, 4))
                pygame.draw.rect(surface, (220, 50, 50), (bar_x, bar_y, int(bar_w * hp_ratio), 4))
                
                if self.armored:
                    pygame.draw.ellipse(surface, (200, 200, 200), (x - 12, y - sh//2, 24, 12), 2)
        else:
            color = (200, 220, 255) if self.kind == "tế bào thực bào" else (150, 30, 30) if self.kind == "kẻ bò trườn" else (150, 50, 200)
            if self.armored: color = (min(color[0]+50, 255), min(color[1]+50, 255), min(color[2]+50, 255))
            pygame.draw.circle(surface, color, (x, y), self.radius)
            if self.armored:
                pygame.draw.circle(surface, (255, 255, 255), (x, y), self.radius, 2)

class Resource:
    def __init__(self, kind, y_range=(100, 3000)):
        # Tìm vị trí hợp lệ (không phải tường) - Giúp cây không bị "mắc" ở khoảng tường to
        px, py = random.randint(100, MAP_W-100), random.randint(y_range[0], y_range[1])
        for _ in range(50):
            tx, ty = random.randint(100, MAP_W-100), random.randint(y_range[0], y_range[1])
            col, row = int(tx // 64), int(ty // 64)
            if 0 <= row < len(map_data) and 0 <= col < len(map_data[0]):
                if map_data[row][col] == 0:
                    px, py = tx, ty
                    break
        self.pos = [px, py]
        self.kind = kind
        self.amount = random.randint(2, 5)
        self.radius = 12 # Giảm nhỏ lại để không bị "mắc" khi đi qua
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        if self.kind == "cây sồi non":
            if "item_cay" in SPRITES and SPRITES["item_cay"]:
                spr = pygame.transform.scale(SPRITES["item_cay"], (50, 55))
                surface.blit(spr, (x - 25, y - 55))
            else:
                pygame.draw.rect(surface, (100, 60, 20), (x-5, y-35, 10, 35))
                pygame.draw.circle(surface, (50, 160, 50), (x, y-38), 14)
        elif self.kind == "suối nước":
            if "item_ho_nuoc" in SPRITES and SPRITES["item_ho_nuoc"]:
                spr = pygame.transform.scale(SPRITES["item_ho_nuoc"], (100, 60))
                surface.blit(spr, (x - 50, y - 30))
            else:
                pygame.draw.ellipse(surface, (30, 80, 120), (x-40, y-15, 80, 30))
                pygame.draw.ellipse(surface, (50, 150, 200), (x-35, y-12, 70, 24))

class Drop:
    def __init__(self, pos, kind, amount):
        self.pos = list(pos)
        self.kind = kind
        self.amount = amount
        self.velocity = [random.uniform(-100, 100), random.uniform(-100, 100)]
        self.z = 20.0
        self.vz = random.uniform(100, 200)
    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt; self.pos[1] += self.velocity[1] * dt
        self.velocity[0] *= 0.9; self.velocity[1] *= 0.9
        self.z += self.vz * dt; self.vz -= 400 * dt
        if self.z <= 0:
            self.z = 0; self.vz = -self.vz * 0.5
            if abs(self.vz) < 10: self.vz = 0
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos); y -= int(self.z)
        # Dung sprite neu co, neu khong dung circle
        drop_icon_map = {
            "thit thu": "item_thit_thu",
            "go soi":   "item_go_soi",
            "nuoc suoi": "item_ho_nuoc",
            "da thu giap": "item_da_thu",
        }
        # Normalize key de match
        norm = self.kind.replace("ịt", "t").replace("ồ", "o").replace("ố", "o").replace("ủ", "u").replace("ứ", "u").replace("ấ", "a").replace("ầ", "a")
        icon_key = f"item_{norm.replace(' ','_')}"
        
        sprite_map = {
            "thịt thú": "item_thit_thu",
            "gỗ sồi":   "item_go_soi",
            "nước suối": "item_ho_nuoc",
            "da thú giáp": "item_da_thu",
        }
        skey = sprite_map.get(self.kind)
        if skey and skey in SPRITES and SPRITES[skey]:
            spr = pygame.transform.scale(SPRITES[skey], (28, 22))
            surface.blit(spr, (x - 14, y - 11))
        else:
            colors = {"nấm linh chi":(220,220,200), "dược thảo":(180,150,80), "thịt thú":(200,50,50), "da thú giáp":(150,200,255), "gỗ sồi":(139,90,43), "nước suối":(100,200,255), "nhựa cây độc":(220,50,180)}
            pygame.draw.circle(surface, colors.get(self.kind, (255,255,255)), (x, y), 8)

class PlacedItem:
    def __init__(self, pos, kind):
        self.pos = list(pos); self.kind = kind
        self.timer = 120.0 if kind == "lửa trại" else 0
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        if self.kind in SPRITES and SPRITES[self.kind]:
            surface.blit(pygame.transform.scale(SPRITES[self.kind], (32, 32)), (x - 16, y - 16))
        else:
            pygame.draw.rect(surface, (255,100,0) if self.kind == "lửa trại" else (80,80,80), (x-10, y-10, 20, 20))

class Decoration:
    def __init__(self, y_range=(0, 20000)):
        self.pos = [random.randint(0, MAP_W), random.randint(y_range[0], y_range[1])]
        self.kind = random.choice(["grass_1", "grass_2", "rock_2", "rock"])
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        if self.kind in SPRITES and SPRITES[self.kind]:
            sprite = SPRITES[self.kind]
            surface.blit(sprite, (x - sprite.get_width()//2, y - sprite.get_height() + 10))

class SpaceDecoration:
    SPACE_OBJECTS = [
        # (sprite_key, display_size)
        ("space_trai_dat",    120),
        ("space_hoa_tinh",    100),
        ("space_mat_trang",    80),
        ("space_bang_tinh",    90),
        ("space_sieu_tan_tinh", 180),
        ("space_ho_den",       200),
        ("space_thien_ha",     220),
    ]
    def __init__(self, placed_positions):
        # Chon ngau nhien object
        key, size = random.choice(self.SPACE_OBJECTS)
        self.kind = key
        self.size = size + random.randint(-15, 15)
        self.phase = random.uniform(0, 6.28)
        
        # Dat vi tri tranh de len nhau: thu toi da 30 lan
        min_dist = self.size + 80  # khoang cach toi thieu giua 2 object
        for _ in range(30):
            px = random.randint(100, MAP_W - 100)
            py = random.randint(-4800, -200)
            ok = all(math.hypot(px - ox, py - oy) > min_dist for ox, oy in placed_positions)
            if ok:
                break
        self.pos = [px, py]
        placed_positions.append((px, py))

    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        # Kiem tra trong man hinh
        if x < -self.size or x > WIDTH + self.size or y < -self.size or y > HEIGHT + self.size:
            return
        if self.kind in SPRITES and SPRITES[self.kind]:
            # Pulse effect nhe
            pulse = 1.0 + 0.03 * math.sin(pygame.time.get_ticks() * 0.001 + self.phase)
            s = max(1, int(self.size * pulse))
            spr = pygame.transform.scale(SPRITES[self.kind], (s, s))
            surface.blit(spr, (x - s // 2, y - s // 2))


class QuestSystem:
    def __init__(self):
        self.tier = 1
        self.stats = {"nấm linh chi": 0, "dược thảo": 0, "Slime Bùn Bùn": 0, "Yêu Tinh Rừng": 0, "Quái Vật Bóng Đêm": 0, "lửa trại": 0, "days": 0}
        self.completed = False
        
    def get_objective(self, player):
        if not ship_repaired:
            return "NHIỆM VỤ: SỬA TÀU (10 Nấm, 10 Dược thảo, 5 Da thú, 5 Nhựa độc) - Ấn [P] gần tàu", False
        
        if self.tier == 1: return "Tầng 1: Diệt 10 Slime (Phần thưởng: +50 HP)", self.stats["Slime Bùn Bùn"] >= 10
        elif self.tier == 2: return "Tầng 2: Thu thập 10 Thịt thú (Phần thưởng: +100 Stamina)", player.inventory.get("thịt thú", 0) >= 10
        elif self.tier == 3: return "Tầng 3: Thâm nhập vào ĐẦM LẦY ĐỘC (8000m)", player.pos[1] >= 8000
        elif self.tier == 4: return "Tầng 4: Thanh tẩy tà khí ở THUNG LŨNG SƯƠNG MÙ (12000m)", player.pos[1] >= 12000
        elif self.tier == 5: return "Tầng 5: CHẠM ĐẾN LÕI RỪNG CỔ ĐẠI (16000m) ĐỂ TIÊU DIỆT TÀ THẦN", player.pos[1] >= 16000
        else: return "LÕI RỪNG CỔ ĐẠI ĐÃ BỊ TIÊU DIỆT! KHU RỪNG ĐÃ ĐƯỢC THANH TẨY!", False


    def check(self, player):
        if self.completed: return
        msg, done = self.get_objective(player)
        if done:
            if self.tier == 1:
                player.max_hp += 50; player.hp = player.max_hp; player.inventory["thịt thú"] += 5
                show_msg("Xong T1! Diệt 10 Vi Rút! +50 HP, +5 Thịt thú")
            elif self.tier == 2:
                player.vision_radius += 100; player.max_stamina += 100; player.stamina = player.max_stamina
                show_msg("Xong T2! Khả năng phân tích nâng cao! +100 Thể lực")
            elif self.tier == 3:
                player.speed += 30; player.max_hp += 50; player.hp = player.max_hp
                show_msg("Xong T3! Xâm nhập ĐẦM LẦY ĐỘC! Tốc độ tăng, +50 HP")
            elif self.tier == 4:
                player.base_damage += 30
                show_msg("Xong T4! Vào THUNG LŨNG SƯƠNG MÙ! Sức mạnh tăng vọt!") 
            elif self.tier == 5:
                self.completed = True
                show_msg("ĐÃ TIÊU DIỆT TÀ THẦN RỪNG SÂU! KHU RỪNG ĐÃ ĐƯỢC THANH TẨY!")
            if self.tier <= 5: self.tier += 1

global_genes = {'speed': 0, 'max_hp': 0, 'vision': 0, 'start_sword': False, 'sanity_resist': False}

# === GAME STATE INIT ===
game_state = "MENU"
char_selection = "warrior"
spaceship_type = "Trực Thăng Trinh Sát"
ship_repaired = False # Tàu bắt đầu ở trạng thái hỏng
intro_timer = 0
intro_pos = [WIDTH//2, -100]
starting_weapon = "None"
intro_msg = ""
running = True
show_crafting = False
show_quest = False   # Tab de mo/dong quest panel

dna_options = []
def generate_dna():
    global dna_options
    pool = [
        ("Chân màng (+20% Tốc độ)", "speed", 40),
        ("Siêu thể lực (+100 Máu tối đa)", "max_hp", 100),
        ("Săn mồi (Bắt đầu với kiếm)", "start_sword", True),
        ("Tầm nhìn đêm (+100 Tầm nhìn)", "vision", 100),
        ("Máu lạnh (Giảm tụt Tâm trí)", "sanity_resist", True)
    ]
    random.shuffle(pool)
    dna_options = pool[:3]

dna_rects = [pygame.Rect(WIDTH//2 - 200, 300 + i*70, 400, 50) for i in range(3)]

# === KHO DO (STORAGE) ===
storage_inventory = {}
show_storage = False

class Storage:
    def __init__(self, pos):
        self.pos = list(pos)
        self.radius = 60
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        pygame.draw.rect(surface, (60, 40, 10), (x-25, y-20, 50, 35), border_radius=6)
        pygame.draw.rect(surface, (200, 160, 50), (x-25, y-20, 50, 35), 2, border_radius=6)
        pygame.draw.rect(surface, (180, 140, 30), (x-25, y-20, 50, 10), border_radius=4)
        pygame.draw.line(surface, (200, 160, 50), (x-25, y-10), (x+25, y-10), 2)
        lbl = small_font.render("KHO", True, (255, 220, 100))
        surface.blit(lbl, (x - lbl.get_width()//2, y - 38))
        # Hien thi khoang cach
        if 'player' in dir():
            pass  # drawn in main loop

def draw_storage_ui():
    """Ve giao dien kho do 2 cot"""
    panel_w, panel_h = 700, 460
    px = WIDTH//2 - panel_w//2
    py = HEIGHT//2 - panel_h//2
    surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (15, 15, 25, 240), (0, 0, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(surf, (200, 160, 50, 255), (0, 0, panel_w, panel_h), 2, border_radius=12)
    screen.blit(surf, (px, py))

    # Tieu de
    title = font.render("=== KHO DO ===", True, (255, 220, 100))
    screen.blit(title, (px + panel_w//2 - title.get_width()//2, py + 15))

    # Cot trai: Tui do nguoi choi
    screen.blit(font.render("TUI DO (1-9 de gui)", True, (150, 220, 255)), (px + 20, py + 50))
    items = [(k, v) for k, v in player.inventory.items() if v > 0]
    for i, (k, v) in enumerate(items[:9]):
        col = (255, 255, 100) if i < 9 else (150, 150, 150)
        screen.blit(small_font.render(f"{i+1}. {k}: {v}", True, col), (px + 20, py + 80 + i*35))

    # Duong chia
    pygame.draw.line(screen, (200, 160, 50), (px + panel_w//2, py + 45), (px + panel_w//2, py + panel_h - 45), 1)

    # Cot phai: Kho
    screen.blit(font.render("KHO (Q-O de lay)", True, (150, 255, 150)), (px + panel_w//2 + 15, py + 50))
    stored = [(k, v) for k, v in storage_inventory.items() if v > 0]
    for i, (k, v) in enumerate(stored[:9]):
        col = (200, 255, 200)
        screen.blit(small_font.render(f"{i+1}. {k}: {v}", True, col), (px + panel_w//2 + 15, py + 80 + i*35))

    # Huong dan
    hint = small_font.render("B: Dong kho  |  1-9: Gui do  |  Q-O: Lay do", True, (180, 180, 180))
    screen.blit(hint, (px + panel_w//2 - hint.get_width()//2, py + panel_h - 35))




def reset_game(skip_intro=False):
    global player, camera, animals, resources, drops, placed_items, messages, time_of_day, game_over
    global quest_system, decorations, landed_ship_pos, day_counter, planet_awareness, sanity, game_state, intro_timer
    
    game_state = "SURVIVAL" if skip_intro else "INTRO"
    intro_timer = 4.0
    planet_awareness = 0.0
    sanity = 100.0
    quest_system = QuestSystem()
    day_counter = 0

    # --- INIT TILEMAP ---
    global map_data, TILE_SIZE, pathfinder
    TILE_SIZE = 64
    MAP_COLS = int(MAP_W / TILE_SIZE)
    MAP_ROWS = int(MAP_H / TILE_SIZE)
    
    # 1: Tường (Wall), 0: Đi được (Floor)
    map_data = [[1 for _ in range(MAP_COLS)] for _ in range(MAP_ROWS)]
    # Random walk đào hầm từ bề mặt xuống lõi
    cx = MAP_COLS // 2
    for y in range(MAP_ROWS):
        # Đào hang tròn xung quanh đường đi chính
        radius = random.randint(3, 6)
        if y < int(LAYERS["SURFACE"][1]/TILE_SIZE):
            radius = 7 # Thu nhỏ không gian tầng bề mặt theo ý user ("khoảng nhỏ thôi")
            
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                if dx*dx + dy*dy <= radius*radius:
                    nx, ny = cx + dx, y + dy
                    if 0 <= nx < MAP_COLS and 0 <= ny < MAP_ROWS:
                        map_data[ny][nx] = 0
        
        # Đường đi dích dắc dần xuống dưới
        cx += random.choice([-3, -2, -1, 0, 1, 2, 3])
        cx = max(10, min(MAP_COLS - 10, cx))

    # Đảm bảo khu vực bề mặt (15 block trên cùng) luôn trống hoàn toàn
    for y in range(15):
        for x in range(MAP_COLS):
            map_data[y][x] = 0
            
    pathfinder = Pathfinder(map_data)
    # --------------------

    player = Player(char_selection)
    player.speed += global_genes['speed']
    player.max_hp += global_genes['max_hp']
    player.hp = player.max_hp
    player.vision_radius += global_genes['vision']
    if global_genes['start_sword']: player.inventory['dao găm'] = 1
    camera = Camera()
    landed_ship_pos = [MAP_W//2, 300]
    
    animals = []
    # Tăng mật độ quái để người chơi không cảm thấy trống trải
    # SURFACE: Alien beasts
    for _ in range(40): animals.append(Animal("Slime Bùn Bùn", LAYERS["SURFACE"]))
    for _ in range(30): animals.append(Animal("Yêu Tinh Rừng", LAYERS["SURFACE"]))
    
    # UNDERGROUND & INFECTED: Dangerous parasites
    for _ in range(40): animals.append(Animal("Yêu Tinh Rừng", LAYERS["UNDERGROUND"]))
    for _ in range(30): animals.append(Animal("Quái Vật Bóng Đêm", LAYERS["INFECTED"]))
    
    # ORGANIC & CORE: Horrors
    for _ in range(50): animals.append(Animal("Quái Vật Bóng Đêm", LAYERS["ORGANIC"]))
    
    resources = []
    # SURFACE: Bio-trees & Water Lakes
    for _ in range(50):
        resources.append(Resource("cây sồi non", LAYERS["SURFACE"]))
    for _ in range(30):
        resources.append(Resource("suối nước", LAYERS["SURFACE"]))
    
    # UNDERGROUND & BEYOND: Bio-forests & underground water
    # Cang vao sau cang nhieu cay (khong the xuyen qua)
    # CAN TRONG CÁC KHOẢNG NHỎ (CAVES)
    for _ in range(150):
        resources.append(Resource("cây sồi non", LAYERS["UNDERGROUND"]))
    for _ in range(250):
        resources.append(Resource("cây sồi non", LAYERS["INFECTED"]))
    for _ in range(400):
        resources.append(Resource("cây sồi non", LAYERS["ORGANIC"]))
        
    for _ in range(50):
        resources.append(Resource("suối nước", [random.randint(0, MAP_W), random.randint(LAYERS["UNDERGROUND"][0], LAYERS["ORGANIC"][1])]))

    decorations = []
    # SURFACE decorations
    for _ in range(80): decorations.append(Decoration(LAYERS["SURFACE"]))
    # DEEPER decorations
    for _ in range(100): decorations.append(Decoration((4000, 20000)))

    # SPACE decorations - hanh tinh va thien the, khong de len nhau
    global space_decorations
    _space_placed = []
    space_decorations = [SpaceDecoration(_space_placed) for _ in range(25)]
    drops = []
    placed_items = []
    messages = []
    time_of_day = 0.0

    # Kho do - dat gan vi tri xuat phat
    global storage_inventory, storage_obj, show_storage
    storage_inventory = {k: 0 for k in [
        "thịt thú", "nấm linh chi", "gỗ sồi", "nước suối",
        "dược thảo", "nhựa cây độc", "da thú giáp",
        "lửa trại", "bẫy thú", "đuốc",
        "dao găm", "kiếm gỗ", "vũ khí cường hóa",
        "áo choàng lá", "giáp da", "bùa rừng sâu",
        "mặt nạ phòng độc", "bùa hộ mệnh", "thảo dược giải độc", "giáp cổ đại"
    ]}
    show_storage = False
    storage_obj = Storage([MAP_W//2 - 150, 320])  # Ke ben tau

    # TỐI ƯU HÓA: Bỏ discovery fog cũ vì gây lag cực nặng. 
    # Chỉ dùng Depth-based Fog trong vòng lặp main.
    game_over = False

reset_game()           # Khởi tạo các object (player, animals...)
game_state = "MENU"   # Nhưng bắt đầu ở Menu, không phải Intro

def show_msg(text):
    messages.append({"text": text, "time": 4.0})
    if len(messages) > 6:
        messages.pop(0)

RECIPES = {
    # Tieu hao
    "lửa trại": {"gỗ sồi": 3, "nấm linh chi": 2},
    "bẫy thú":      {"gỗ sồi": 2, "nấm linh chi": 5},
    "đuốc":         {"gỗ sồi": 2, "nhựa cây độc": 1},
    # Vũ khí - 3 tier (cộng dồn, không cần tiến trước)
    "dao găm":         {"gỗ sồi": 5,  "nấm linh chi": 10},              # +25 DMG
    "kiếm gỗ":  {"gỗ sồi": 10, "dược thảo": 5, "thịt thú": 5},          # +40 DMG
    "vũ khí cường hóa":  {"nhựa cây độc": 10, "dược thảo": 10, "da thú giáp": 5},  # +70 DMG
    # Giáp - 3 tier
    "áo choàng lá":        {"gỗ sồi": 8,  "dược thảo": 10, "thịt thú": 5},       # +100 HP
    "giáp da": {"nước suối": 10, "dược thảo": 10, "da thú giáp": 10},  # +200 HP
    "bùa rừng sâu":   {"nhựa cây độc": 15, "da thú giáp": 15, "dược thảo": 10},  # +350 HP
    # Bo bao ho tang sau (yeu cau de vao)
    "mặt nạ phòng độc":    {"gỗ sồi": 10, "nấm linh chi": 8, "dược thảo": 5},      # Vao RỪNG GIÀ
    "bùa hộ mệnh":         {"dược thảo": 15, "da thú giáp": 10, "thịt thú": 10},   # Vao ĐẦM LẦY ĐỘC
    "thảo dược giải độc":  {"nước suối": 12, "da thú giáp": 12, "dược thảo": 8},   # Vao THUNG LŨNG SƯƠNG MÙ
    "giáp cổ đại":  {"nhựa cây độc": 20, "da thú giáp": 20, "dược thảo": 15},      # Vao LÕI RỪNG
}

UNIQUE_ITEMS = {"dao găm", "kiếm gỗ", "vũ khí cường hóa",
               "áo choàng lá", "giáp da", "bùa rừng sâu"}

def craft(item_name):
    inv = player.inventory
    if item_name in UNIQUE_ITEMS and inv.get(item_name, 0) >= 1:
        show_msg(f"Ban da co {item_name} roi!"); return
    cost = RECIPES[item_name]
    if all(inv.get(r, 0) >= n for r, n in cost.items()):
        for r, n in cost.items(): inv[r] -= n
        inv[item_name] = inv.get(item_name, 0) + 1
        show_msg(f"Che tao: {item_name}!")
        # Ap dung hieu ung trang bi ngay lap tuc
        if item_name == "áo choàng lá":
            player.max_hp += 100; player.hp = min(player.hp + 100, player.max_hp)
            show_msg("+100 HP tu Giap Mang!")
        elif item_name == "giáp da":
            player.max_hp += 200; player.hp = min(player.hp + 200, player.max_hp)
            show_msg("+200 HP tu Giap Huyet Thanh!")
        elif item_name == "bùa rừng sâu":
            player.max_hp += 350; player.hp = min(player.hp + 350, player.max_hp)
            show_msg("+350 HP tu Giap Dot Bien!")
    else:
        show_msg(f"Thieu nguyen lieu: {item_name}")


# === SPACE MODE CLASSES ===
import math


class SpaceShip:
    def __init__(self, ship_type):
        self.ship_type = ship_type
        self.pos = [WIDTH//2, HEIGHT//2]
        self.angle = 0.0
        self.velocity = [0.0, 0.0]
        self.shoot_cd = 0
        
        # Thiết lập điểm mạnh và yếu cho từng loại tàu
        if self.ship_type == "Trực Thăng Trinh Sát":
            self.max_hp = 600       # Yếu: HP thấp
            self.speed = 600.0      # Mạnh: Rất nhanh
            self.turn_speed = 240.0 # Mạnh: Xoay nhanh lẹ
            self.gravity_res = 1.0  # Yếu: Dễ bị lỗ đen hút
        else: # Trực Thăng Bọc Thép
            self.max_hp = 1500      # Mạnh: Rất trâu
            self.speed = 300.0      # Yếu: Chậm chạp
            self.turn_speed = 120.0 # Yếu: Xoay chậm
            self.gravity_res = 0.5  # Mạnh: Nấm lực hút tốt hơn (ổn định)
            
        self.hp = self.max_hp

    def update(self, dt, keys, blackholes):
        if keys[pygame.K_LEFT]: self.angle += self.turn_speed * dt
        if keys[pygame.K_RIGHT]: self.angle -= self.turn_speed * dt
        if keys[pygame.K_UP]:
            rad = math.radians(self.angle)
            self.velocity[0] += math.cos(rad) * self.speed * dt
            self.velocity[1] -= math.sin(rad) * self.speed * dt
            
        # Gravity
        for bh in blackholes:
            dx = bh.pos[0] - self.pos[0]
            dy = bh.pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if 10 < dist < 2000:
                force = bh.mass / dist * self.gravity_res
                self.velocity[0] += (dx/dist) * force * dt
                self.velocity[1] += (dy/dist) * force * dt
            
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
        
        # Friction
        self.velocity[0] *= 0.99
        self.velocity[1] *= 0.99
        self.shoot_cd -= dt

    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        
        sprite_key = "flesh_pod" if spaceship_type == "Trực Thăng Trinh Sát" else "nerve_cruiser"
        if sprite_key in SPRITES and SPRITES[sprite_key]:
            base_sprite = pygame.transform.scale(SPRITES[sprite_key], (80, 80))
            # The ships are vertical, so we might need to adjust rotation if angle 0 is right
            # Standard pygame rotate: 0 is unchanged (up in many assets, right in others)
            # My current angle logic: 0 is right. These ships look oriented UP.
            # So add -90 to rotate them to face the movement direction.
            rotated = pygame.transform.rotate(base_sprite, self.angle - 90)
            surface.blit(rotated, (x - rotated.get_width()//2, y - rotated.get_height()//2))
            
            # Draw thruster glow
            rad = math.radians(self.angle)
            tx = x - math.cos(rad) * 40
            ty = y + math.sin(rad) * 40
            color = (255, 50, 50) if spaceship_type == "Trực Thăng Trinh Sát" else (50, 200, 255)
            pygame.draw.circle(surface, color, (int(tx), int(ty)), random.randint(10, 18))
        else:
            pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), 20)

class Bullet:
    def __init__(self, pos, angle):
        self.pos = list(pos)
        self.velocity = [math.cos(math.radians(angle))*800, -math.sin(math.radians(angle))*800]
        self.life = 2.0
    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
        self.life -= dt
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        pygame.draw.circle(surface, (255, 255, 100), (int(x), int(y)), 5)

class Asteroid:
    def __init__(self, pos):
        self.pos = list(pos)
        self.radius = random.randint(50, 90)
        self.velocity = [random.uniform(-40, 40), random.uniform(-40, 40)]
        self.hp = self.radius
        # CHỈ DÙNG CÁC HÀNH TINH CHUẨN
        self.type = random.choice(["planet_earth", "planet_lava", "planet_grey", "planet_ice"])
    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        skey = f"space_{self.type}"
        if skey in SPRITES and SPRITES[skey]:
            spr = pygame.transform.scale(SPRITES[skey], (self.radius*2, self.radius*2))
            surface.blit(spr, (x - self.radius, y - self.radius))
        else:
            pygame.draw.circle(surface, (150, 50, 50), (int(x), int(y)), self.radius)

class Blackhole:
    def __init__(self, pos):
        self.pos = list(pos)
        self.radius = 280
        self.mass = 9000.0
    def draw(self, surface, cam):
        x, y = cam.apply(self.pos)
        if "space_black_hole" in SPRITES and SPRITES["space_black_hole"]:
            spr = pygame.transform.scale(SPRITES["space_black_hole"], (self.radius*2, self.radius*2))
            surface.blit(spr, (x - self.radius, y - self.radius))
        else:
            pygame.draw.circle(surface, (10, 0, 20), (int(x), int(y)), self.radius)
            pygame.draw.circle(surface, (100, 0, 200), (int(x), int(y)), self.radius, 2)

def init_space():
    global space_ship, asteroids, space_camera, blackholes, space_bullets, landed_ship_pos
    space_ship = SpaceShip(spaceship_type)
    space_camera = Camera()
    space_ship.pos = [0, 0]
    space_bullets = []
    # CHỈ GIỮ LẠI 4 HÀNH TINH VÀ HỐ ĐEN (ĐÃ LỌC SẠCH CÂY VÀ HỒ)
    asteroids = [Asteroid([random.randint(-7000, 7000), random.randint(-7000, 7000)]) for _ in range(250)]
    blackholes = [Blackhole([random.randint(-5000, 5000), random.randint(-5000, 5000)]) for _ in range(15)]
time_tick = 0  # Khai báo sớm để draw_menu() có thể dùng

def draw_menu():
    screen.fill((10, 3, 3))
    
    # Nền gradient tối
    for i in range(HEIGHT):
        darkness = max(0, 40 - int(i * 40 / HEIGHT))
        pygame.draw.line(screen, (darkness, 0, 0), (0, i), (WIDTH, i))
    
    # Tiêu đề
    title = title_font.render("KHÁNG THỂ", True, (255, 60, 60))
    shadow = title_font.render("KHÁNG THỂ", True, (80, 0, 0))
    screen.blit(shadow, (WIDTH//2 - title.get_width()//2 + 3, 53))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    subtitle = font.render("Chiến đấu trong cơ thể người", True, (180, 80, 80))
    screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 130))
    
    # ── CHỌN NHÂN VẬT ──
    chars = ["warrior", "red_hood", "skeleton"]
    char_labels = {"warrior": "Penicillin", "red_hood": "Amoxicillin", "skeleton": "Tetracycline"}
    char_stats = {
        "warrior":   "HP: 250  |  Speed: Vừa  |  DMG: 25  |  Chuyên: Cận chiến",
        "red_hood": "HP: 200  |  Speed: Cao   |  DMG: 15  |  Chuyên: Tấn công diện rộng",
        "skeleton": "HP: 180  |  Speed: Thấp  |  DMG: 40  |  Chuyên: Tấn công phép",
    }
    section_x = 80
    screen.blit(font.render("── CHỌN KHÁNG SINH ──", True, (100, 255, 150)), (section_x, 175))
    for i, ch in enumerate(chars):
        cx = section_x + i * 190
        selected = (ch == char_selection)
        border_col = (255, 220, 0) if selected else (80, 80, 80)
        bg_col = (40, 40, 20) if selected else (20, 20, 20)
        card = pygame.Rect(cx, 200, 175, 160)
        pygame.draw.rect(screen, bg_col, card, border_radius=8)
        pygame.draw.rect(screen, border_col, card, 2, border_radius=8)
        
        # Preview nhân vật
        anim_key = f"{ch}_idle"
        if anim_key in SPRITES and SPRITES[anim_key]:
            frames = SPRITES[anim_key]
            sp = frames[int(pygame.time.get_ticks()/120) % len(frames)]
            sp = pygame.transform.scale(sp, (70, 70))
            screen.blit(sp, (cx + 52, 205))
        
        lbl = font.render(char_labels[ch], True, (255,220,0) if selected else (180,180,180))
        screen.blit(lbl, (cx + card.w//2 - lbl.get_width()//2, 278))
        stat = small_font.render("[ Đang chọn ]", True, (255,200,0)) if selected else small_font.render("Click để chọn", True, (120,120,120))
        screen.blit(stat, (cx + card.w//2 - stat.get_width()//2, 300))
    
    # Thông số nhân vật hiện tại
    stat_txt = small_font.render(char_stats.get(char_selection, ""), True, (200, 200, 150))
    screen.blit(stat_txt, (section_x, 370))

    # ── CHỌN TRỰC THĂNG ĐỔ BỘ ──
    ships = ["Trực Thăng Trinh Sát", "Trực Thăng Bọc Thép"]
    ship_descs = {
        "Trực Thăng Trinh Sát":     ("Giáp: Nhẹ, Cơ động: Cao", "Tốc độ di chuyển rất cao"),
        "Trực Thăng Bọc Thép": ("Giáp: Nặng, Cơ động: Thấp", "Chống chịu tốt"),
    }
    ship_keys = {"Trực Thăng Trinh Sát": "flesh_pod", "Trực Thăng Bọc Thép": "nerve_cruiser"}
    screen.blit(font.render("── TRỰC THĂNG ĐỔ BỘ ──", True, (100, 255, 200)), (section_x, 400))
    for i, sh in enumerate(ships):
        sx = section_x + i * 400
        selected = (sh == spaceship_type)
        border_col = (100, 180, 255) if selected else (60, 60, 80)
        bg_col = (10, 20, 40) if selected else (15, 15, 20)
        scard = pygame.Rect(sx, 425, 380, 100)
        pygame.draw.rect(screen, bg_col, scard, border_radius=8)
        pygame.draw.rect(screen, border_col, scard, 2, border_radius=8)
        
        # Preview tàu
        sk = ship_keys[sh]
        if sk in SPRITES and SPRITES[sk]:
            sp = pygame.transform.scale(SPRITES[sk], (60, 60))
            screen.blit(sp, (sx + 10, 432))
        
        name_txt = font.render(sh, True, (100,200,255) if selected else (140,140,180))
        screen.blit(name_txt, (sx + 78, 432))
        
        # In mô tả trên 2 dòng
        line1 = small_font.render(ship_descs[sh][0], True, (160,160,200))
        line2 = small_font.render(ship_descs[sh][1], True, (160,160,200))
        screen.blit(line1, (sx + 78, 455))
        screen.blit(line2, (sx + 78, 470))
        
        sel_txt = small_font.render("[ Đang chọn ]", True, (100,200,255)) if selected else small_font.render("Click để chọn", True, (130,130,150))
        screen.blit(sel_txt, (sx + 78, 490))

    # Nút Start
    pulse = abs(math.sin(time_tick * 2)) * 30
    start_color = (int(120 + pulse), int(20 + pulse//3), int(20 + pulse//3))
    pygame.draw.rect(screen, start_color, start_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 100, 100), start_rect, 2, border_radius=10)
    start_lbl = font.render("BẮT ĐẦU CUỘC HÀNH TRÌNH", True, (255, 240, 240))
    screen.blit(start_lbl, (start_rect.x + start_rect.w//2 - start_lbl.get_width()//2, start_rect.y + 12))


# Rects cho menu mới (click theo vùng card)
start_rect = pygame.Rect(WIDTH//2 - 200, 545, 400, 50)
# Char cards: 3 cards, mỗi cái 175px, cách nhau 190px, bắt đầu từ x=80
_chars = ["warrior", "red_hood", "skeleton"]
char_cards = [pygame.Rect(80 + i*190, 200, 175, 160) for i in range(3)]
# Ship cards: 2 cards
_ships = ["Trực Thăng Trinh Sát", "Trực Thăng Bọc Thép"]
ship_cards = [pygame.Rect(80 + i*400, 425, 380, 100) for i in range(2)]
# Compat stubs cho code cũ
ship_rect = ship_cards[0]
wpn_rect = pygame.Rect(0, 0, 1, 1)  # Không dùng nữa
print("Assets loaded, starting game loop...")
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    time_tick += dt
    keys = pygame.key.get_pressed()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if game_state == "MENU":
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_rect.collidepoint(event.pos):
                    reset_game(skip_intro=False)
                    if spaceship_type == "Trực Thăng Trinh Sát": player.speed += 80    # Trực Thăng Trinh Sát: Nhanh hơn
                    elif spaceship_type == "Trực Thăng Bọc Thép": player.max_hp += 200; player.hp = player.max_hp  # Trực Thăng Bọc Thép: Trâu hơn
                    intro_timer = 4.0
                    intro_pos = [WIDTH//2, -200]
                    game_state = "INTRO"
                else:
                    # Click card nhân vật
                    for i, card in enumerate(char_cards):
                        if card.collidepoint(event.pos):
                            char_selection = _chars[i]
                    # Click card tàu
                    for i, scard in enumerate(ship_cards):
                        if scard.collidepoint(event.pos):
                            spaceship_type = _ships[i]
                    
        elif game_state == "DNA_MENU":
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for i, rect in enumerate(dna_rects):
                    if rect.collidepoint(mx, my) and i < len(dna_options):
                        opt = dna_options[i]
                        global_genes[opt[1]] = opt[2]
                        reset_game(skip_intro=True)  # Vào thẳng Survival, không cần Intro
                        break
                        
        elif game_state == "SPACE":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "SURVIVAL"

        elif game_state == "SURVIVAL":
            if event.type == pygame.KEYDOWN:
                if game_over:
                    if event.key == pygame.K_r: reset_game(skip_intro=True)
                    if event.key == pygame.K_m: game_state = "MENU"
                    continue
                    
                if event.key == pygame.K_o:
                    player.auto_play = not getattr(player, "auto_play", False)
                    show_msg(f"AUTO-PLAY: {'BẬT' if player.auto_play else 'TẮT'}")

                if event.key == pygame.K_e or event.key == pygame.K_f:
                    interacted = False
                    # 1. Khai thác tài nguyên (Dùng cả E và F đều được)
                    for r in resources[:]:
                        if distance(player.pos, r.pos) < r.radius + 35:
                            if r.kind == "cây sồi non": 
                                drops.append(Drop(r.pos, "gỗ sồi", random.randint(2, 4)))
                                show_msg("Đã thu thập Gỗ sồi từ sợi collagen.")
                            elif r.kind == "suối nước":
                                drops.append(Drop(r.pos, "nước suối", random.randint(2, 4)))
                                show_msg("Đã múc được Nước suối từ hồ.")
                            
                            resources.remove(r)
                            planet_awareness += 2.0
                            interacted = True
                            break
                    
                    # 2. Tấn công quái vật (Chỉ phím F mới kích hoạt tấn công)
                    if not interacted and event.key == pygame.K_f:
                        if player.attack_cd <= 0 and player.stamina >= 15:
                            player.stamina -= 15
                            player.attack_cd = 0.5
                            hit = False
                            for a in animals[:]:
                                if distance(player.pos, a.pos) < 110:
                                    dmg = player.get_damage()
                                    if getattr(a, "armored", False): dmg *= 0.5
                                    a.hp -= dmg
                                    hit = True
                                    if a.hp <= 0:
                                        quest_system.stats[a.kind] += 1
                                        # Quái vật rơi tài nguyên
                                        drops.append(Drop(a.pos, "thịt thú", random.randint(2, 4)))
                                        drops.append(Drop(a.pos, "nấm linh chi", random.randint(1, 3)))
                                        
                                        if a.kind == "Yêu Tinh Rừng":
                                            drops.append(Drop(a.pos, "da thú giáp", random.randint(1, 2)))
                                            drops.append(Drop(a.pos, "dược thảo", random.randint(2, 4)))
                                            # Thêm một ít nhựa cây độc cho người chơi dễ làm nhiệm vụ đầu
                                            drops.append(Drop(a.pos, "nhựa cây độc", random.randint(1, 2)))
                                        if a.kind == "Quái Vật Bóng Đêm":
                                            drops.append(Drop(a.pos, "nhựa cây độc", random.randint(2, 5)))
                                            
                                        animals.remove(a)
                                        planet_awareness += 5.0
                                        show_msg(f"Đã tiêu diệt {a.kind}")
                            if not hit: show_msg("Đánh hụt!")
                
                if event.key == pygame.K_c:
                    show_crafting = not show_crafting
                    show_storage = False
                if event.key == pygame.K_TAB:
                    show_quest = not show_quest

                if event.key == pygame.K_b:
                    near_storage = distance(player.pos, storage_obj.pos) < storage_obj.radius + 150
                    if near_storage or show_storage:
                        show_storage = not show_storage
                        show_crafting = False
                    else:
                        show_msg("Hãy đến gần Kho để mở (biểu tượng hòm gỗ)")

                # Crafting keys - cấp 1
                if show_crafting and not show_storage:
                    if event.key == pygame.K_1: craft("lửa trại")
                    if event.key == pygame.K_2: craft("bẫy thú")
                    if event.key == pygame.K_3: craft("đuốc")
                    if event.key == pygame.K_4: craft("dao găm")
                    if event.key == pygame.K_5: craft("kiếm gỗ")
                    if event.key == pygame.K_6: craft("vũ khí cường hóa")
                    if event.key == pygame.K_7: craft("áo choàng lá")
                    if event.key == pygame.K_8: craft("giáp da")
                    if event.key == pygame.K_9: craft("bùa rừng sâu")
                    if event.key == pygame.K_0: craft("mặt nạ phòng độc")
                    if event.key == pygame.K_MINUS:  craft("bùa hộ mệnh")
                    if event.key == pygame.K_EQUALS: craft("thảo dược giải độc")

                # Storage keys - gửi và lấy đồ
                if show_storage:
                    items_list = [(k,v) for k,v in player.inventory.items() if v > 0]
                    stored_list = [(k,v) for k,v in storage_inventory.items() if v > 0]
                    num_keys = [pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5,
                                pygame.K_6,pygame.K_7,pygame.K_8,pygame.K_9]
                    withdraw_keys = [pygame.K_q,pygame.K_w,pygame.K_e,pygame.K_r,pygame.K_t,
                                     pygame.K_y,pygame.K_u,pygame.K_i,pygame.K_o]
                    for idx, k in enumerate(num_keys):   # GUI do (1-9)
                        if event.key == k and idx < len(items_list):
                            name, qty = items_list[idx]
                            player.inventory[name] -= qty
                            storage_inventory[name] = storage_inventory.get(name, 0) + qty
                            show_msg(f"Gui {qty}x {name} vao kho")
                    for idx, k in enumerate(withdraw_keys):  # LAY do (Q-O)
                        if event.key == k and idx < len(stored_list):
                            name, qty = stored_list[idx]
                            storage_inventory[name] = 0
                            player.inventory[name] = player.inventory.get(name, 0) + qty
                            show_msg(f"Lay {qty}x {name} tu kho")
                
                # --- Consumables (Chỉ khi không mở menu) ---
                if not show_storage and not show_crafting:
                    if event.key == pygame.K_q:
                        if player.inventory.get("thịt thú", 0) > 0:
                            player.inventory["thịt thú"] -= 1
                            player.hunger = min(player.max_hunger, player.hunger + 30)
                            player.hp = min(player.max_hp, player.hp + 20)
                            show_msg("Đã ăn thịt thú (Protein +30, HP +20).")
                        else:
                            show_msg("Bạn không có thịt thú để ăn!")
                    
                    if event.key == pygame.K_w:
                        if player.inventory.get("nước suối", 0) > 0:
                            player.inventory["nước suối"] -= 1
                            player.thirst = min(player.max_thirst, player.thirst + 40)
                            show_msg("Đã uống nước suối (Nước +40).")
                        else:
                            show_msg("Bạn không có nước suối để uống!")
                
                if event.key == pygame.K_SPACE:
                    if player.inventory.get("lửa trại", 0) > 0:
                        player.inventory["lửa trại"] -= 1
                        placed_items.append(PlacedItem(player.pos, "lửa trại"))
                        quest_system.stats["lửa trại"] += 1
                        show_msg("Đã đặt vùng kháng khuẩn.")
                    elif player.inventory.get("bẫy thú", 0) > 0:
                        player.inventory["bẫy thú"] -= 1
                        placed_items.append(PlacedItem(player.pos, "bẫy thú"))
                        show_msg("Đã đặt bẫy protein.")
                    else:
                        show_msg("Chưa có Bẫy thú hoặc Lửa trại! Hãy bấm C để chế tạo.")
                        
                if event.key == pygame.K_p:
                    if distance(player.pos, landed_ship_pos) < 150:
                        if not ship_repaired:
                            # Điều kiện sửa tàu nâng cao
                            has_items = (player.inventory.get("nấm linh chi", 0) >= 10 and 
                                         player.inventory.get("dược thảo", 0) >= 10 and
                                         player.inventory.get("da thú giáp", 0) >= 5 and 
                                         player.inventory.get("nhựa cây độc", 0) >= 5)
                            
                            if has_items:
                                player.inventory["nấm linh chi"] -= 10
                                player.inventory["dược thảo"] -= 10
                                player.inventory["da thú giáp"] -= 5
                                player.inventory["nhựa cây độc"] -= 5
                                ship_repaired = True
                                show_msg("TÀU ĐÃ ĐƯỢC SỬA! BẠN CÓ THỂ VÀO VŨ TRỤ (Ấn P tiếp)!")
                            else:
                                show_msg("CẦN: 10 Nấm, 10 Dược thảo, 5 Da thú giáp, 5 Nhựa cây độc!")
                        else:
                            game_state = "SPACE"
                            init_space()
                            show_msg("KÍCH HOẠT HỆ MIỄN DỊCH!")
                    else:
                        show_msg("Lỗi: Phải đứng gần Tàu (Điểm màu Tím trên bản đồ)!")

        # --- Xử lý phím ảo từ Auto-Play ---
        if game_state == "SURVIVAL" and not game_over and getattr(player, "auto_play", False):
            if hasattr(player, "simulated_craft_requests"):
                for item in player.simulated_craft_requests:
                    craft(item)
                    show_msg(f"Auto-Craft: Đã tự động chế tạo {item}!")
                player.simulated_craft_requests = []
                
            if getattr(player, "simulated_key_p", False):
                if not ship_repaired:
                    has_items = (player.inventory.get("nấm linh chi", 0) >= 10 and 
                                 player.inventory.get("dược thảo", 0) >= 10 and
                                 player.inventory.get("da thú giáp", 0) >= 5 and 
                                 player.inventory.get("nhựa cây độc", 0) >= 5)
                    if has_items:
                        player.inventory["nấm linh chi"] -= 10
                        player.inventory["dược thảo"] -= 10
                        player.inventory["da thú giáp"] -= 5
                        player.inventory["nhựa cây độc"] -= 5
                        ship_repaired = True
                        show_msg("AUTO: ĐÃ TỰ ĐỘNG SỬA TÀU! CHUẨN BỊ BAY!")
                else:
                    game_state = "SPACE"
                    init_space()
                    show_msg("AUTO: KÍCH HOẠT HỆ MIỄN DỊCH VÀ BAY LÊN!")

            if player.simulated_key_e or player.simulated_key_f:
                interacted = False
                for r in resources[:]:
                    if distance(player.pos, r.pos) < r.radius + 50:
                        if r.kind == "cây sồi non": 
                            drops.append(Drop(r.pos, "gỗ sồi", random.randint(2, 4)))
                            show_msg("Đã thu thập Gỗ sồi từ sợi collagen.")
                        elif r.kind == "suối nước":
                            drops.append(Drop(r.pos, "nước suối", random.randint(2, 4)))
                            show_msg("Đã múc được Nước suối từ hồ.")
                        resources.remove(r)
                        planet_awareness += 2.0
                        interacted = True
                        break
                if not interacted and player.simulated_key_f:
                    if player.attack_cd <= 0 and player.stamina >= 15:
                        player.stamina -= 15
                        player.attack_cd = 0.5
                        hit = False
                        for a in animals[:]:
                            if distance(player.pos, a.pos) < 110:
                                dmg = player.get_damage()
                                if getattr(a, "armored", False): dmg *= 0.5
                                a.hp -= dmg
                                hit = True
                                if a.hp <= 0:
                                    quest_system.stats[a.kind] += 1
                                    drops.append(Drop(a.pos, "thịt thú", random.randint(2, 4)))
                                    drops.append(Drop(a.pos, "nấm linh chi", random.randint(1, 3)))
                                    if a.kind == "Yêu Tinh Rừng":
                                        drops.append(Drop(a.pos, "da thú giáp", random.randint(1, 2)))
                                        drops.append(Drop(a.pos, "dược thảo", random.randint(2, 4)))
                                        drops.append(Drop(a.pos, "nhựa cây độc", random.randint(1, 2)))
                                    if a.kind == "Quái Vật Bóng Đêm":
                                        drops.append(Drop(a.pos, "nhựa cây độc", random.randint(2, 5)))
                                    animals.remove(a)
                                    planet_awareness += 5.0
                                    show_msg(f"Đã tiêu diệt {a.kind}")
                        if not hit: show_msg("Đánh hụt (Auto)!")
                        
            if player.simulated_key_q:
                if player.inventory.get("thịt thú", 0) > 0:
                    player.inventory["thịt thú"] -= 1
                    player.hunger = min(player.max_hunger, player.hunger + 30)
                    player.hp = min(player.max_hp, player.hp + 20)
                    show_msg("Auto: Đã ăn thịt thú.")
            if player.simulated_key_w:
                if player.inventory.get("nước suối", 0) > 0:
                    player.inventory["nước suối"] -= 1
                    player.thirst = min(player.max_thirst, player.thirst + 40)
                    show_msg("Auto: Đã uống nước suối.")

    # === LOGIC UPDATE ===
    if game_state == "INTRO":
        intro_timer -= dt
        intro_pos[1] += 300 * dt
        
        # Thêm hội thoại kịch tính từ AI tàu
        diag_time = 4.0 - intro_timer
        if diag_time < 1.0: intro_msg = "HELIOS-9: Đang thâm nhập bầu khí quyển..."
        elif diag_time < 1.8: intro_msg = "AI TÀU: CẢNH BÁO! PHÁT HIỆN NHỊP ĐẦM LẦY ĐỘC DƯỚI LỚP MÂY!"
        elif diag_time < 2.5: intro_msg = "AI TÀU: IT KNOWS. IT KNOWS. IT KNOWS."
        elif diag_time < 3.2: intro_msg = "AI TÀU: ĐỪNG HẠ CÁNH! CHẠY NGAY!!!"
        else: intro_msg = "CRASH INBOUND..."
        
        if intro_timer <= 0:
            # Vụ nổ va chạm
            game_state = "SURVIVAL"
            player.pos = [MAP_W//2, 500]
            # Awareness bắt đầu thấp để tránh rung liên tục
            planet_awareness = 15.0 
            show_msg("!!! BÙM !!!")
            show_msg("KAI: Tôi còn sống... HELIOS-9 đã tan tành.")
            show_msg("PDA: Hệ thống sinh học xác nhận: ĐANG Ở TRONG MÔ SỐNG.")
            
    elif game_state == "SPACE":
        space_ship.update(dt, keys, blackholes)
        space_camera.update(space_ship.pos)
        if keys[pygame.K_SPACE] and space_ship.shoot_cd <= 0:
            space_ship.shoot_cd = 0.2
            space_bullets.append(Bullet(space_ship.pos, space_ship.angle))
        for b in space_bullets[:]:
            b.update(dt)
            if b.life <= 0: space_bullets.remove(b)
            else:
                for ast in asteroids[:]:
                    if distance(b.pos, ast.pos) < ast.radius:
                        ast.hp -= 25
                        if b in space_bullets: space_bullets.remove(b)
                        if ast.hp <= 0:
                            asteroids.remove(ast)
                        break
        for ast in asteroids: ast.update(dt)
        # Va chạm tàu với hành tinh
        for ast in asteroids:
            if distance(space_ship.pos, ast.pos) < ast.radius + 30:
                space_ship.hp -= 30 * dt # Mat mau lien tuc khi va cham
                # Day tau ra xa
                dx = space_ship.pos[0] - ast.pos[0]
                dy = space_ship.pos[1] - ast.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    space_ship.velocity[0] += (dx/dist) * 15
                    space_ship.velocity[1] += (dy/dist) * 15
        if space_ship.hp <= 0:
            show_msg("TÀU ĐÃ BỊ PHÁ HỦY! TRỞ VỀ MẶT ĐẤT...")
            game_state = "SURVIVAL"
            player.hp -= 50
            player.pos = [MAP_W//2, 500]

    elif game_state == "SURVIVAL":
        time_of_day += dt * 0.02
        if time_of_day >= 1.0:
            time_of_day = 0.0
            day_counter += 1
            quest_system.stats["days"] = day_counter
        if player.hp <= 0:
            game_over = True
            game_state = 'DNA_MENU'
            generate_dna()
        if not game_over:
            player.update(dt, keys, animals, resources, drops, landed_ship_pos)
            camera.update(player.pos)
            quest_system.check(player)

            # === THÔNG BÁO CHUYỂN TẦNG ===
            if player.pos[1] < LAYERS["UNDERGROUND"][0]:
                current_biome = "BÌA RỪNG"
            elif player.pos[1] < LAYERS["INFECTED"][0]:
                current_biome = "RỪNG GIÀ"
            elif player.pos[1] < LAYERS["ORGANIC"][0]:
                current_biome = "ĐẦM LẦY ĐỘC"
            elif player.pos[1] < LAYERS["CORE"][0]:
                current_biome = "THUNG LŨNG SƯƠNG MÙ"
            else:
                current_biome = "LÕI RỪNG CỔ ĐẠI"
                
            if getattr(player, "last_biome", "") != current_biome:
                if getattr(player, "last_biome", "") != "":
                    show_msg(f"★★★ BẠN ĐÃ TIẾN VÀO TẦNG: {current_biome} ★★★")
                player.last_biome = current_biome

            # === KHU VỰC ĐỘC HẠI (Zone Damage) ===
            # Thay vì chặn đường, người chơi sẽ bị mất máu liên tục nếu thiếu đồ bảo hộ
            layer_gates = [
                (LAYERS["CORE"][0],        ["giáp cổ đại"],  "⚠ KHÍ ĐỘC CỔ ĐẠI! Mất máu cực nhanh!", 30.0),
                (LAYERS["ORGANIC"][0],     ["giáp cổ đại", "thảo dược giải độc"],  "⚠ NHIỄM ĐỘC THUNG LŨNG SƯƠNG MÙ! Tế bào thần kinh bị phá hủy!", 20.0),
                (LAYERS["INFECTED"][0],    ["giáp cổ đại", "thảo dược giải độc", "bùa hộ mệnh"],       "⚠ ÁP LỰC TẦNG ĐẦM LẦY ĐỘC! Đang mất máu!", 10.0),
                (LAYERS["UNDERGROUND"][0], ["giáp cổ đại", "thảo dược giải độc", "bùa hộ mệnh", "mặt nạ phòng độc"],   "⚠ KHÔNG KHÍ ĐỘC (RỪNG GIÀ)! Đang bị ngạt!", 5.0),
            ]
            
            for gate_y, valid_items, warn, dmg_rate in layer_gates:
                if player.pos[1] > gate_y:
                    has_protection = any(player.inventory.get(item, 0) > 0 for item in valid_items)
                    if not has_protection:
                        player.hp -= dmg_rate * dt
                        # Chỉ hiển thị cảnh báo nếu trên màn hình chưa có dòng chữ này (tránh spam)
                        if not any(warn in m["text"] for m in messages):
                            show_msg(warn)
                    break  # Đã tìm thấy tầng sâu nhất mà người chơi đang ở, không cần kiểm tra các tầng trên nữa
            
            # === TÂM TRÍ (SANITY) DRAIN theo biome ===
            # Càng xuống sâu, Tâm trí tụt càng nhanh
            if player.pos[1] < LAYERS["UNDERGROUND"][0]:
                sanity_drain = 0.0   # Tầng bề mặt: an toàn
            elif player.pos[1] < LAYERS["INFECTED"][0]:
                sanity_drain = 0.5   # Underground: tụt chậm
            elif player.pos[1] < LAYERS["ORGANIC"][0]:
                sanity_drain = 1.5   # Infected Zone: tụt vừa
            else:
                sanity_drain = 3.0   # Organic/Core: tụt mạnh
            
            # Gene Máu lạnh: giảm 50% tốc độ tụt Tâm trí
            if global_genes.get('sanity_resist'):
                sanity_drain *= 0.5
            
            player.sanity = max(0, player.sanity - sanity_drain * dt)
            
            # Khi Tâm trí cạn: nhân vật run, màn hình rung, mất HP nhẹ
            if player.sanity <= 0:
                player.hp -= 5.0 * dt
                show_msg("TINH THẦN SỤP ĐỔ! BẠN ĐÃ BỎ CUỘC!")
            
            # Tự động nhặt đồ (Auto-pickup - Bán kính rộng hơn)
            for d in drops[:]:
                d.update(dt)
                if distance(player.pos, d.pos) < 65:
                    player.inventory[d.kind] += d.amount
                    drops.remove(d)
                    show_msg(f"Đã nhặt {d.amount} {d.kind}")
                    if d.kind == "nấm linh chi": quest_system.stats["nấm linh chi"] += d.amount
                    if d.kind == "dược thảo": quest_system.stats["dược thảo"] += d.amount
                    
            # Chỉ update động vật nằm trong viewport + margin
            VIEW_MARGIN = 300
            viewport_left = camera.x - VIEW_MARGIN
            viewport_right = camera.x + WIDTH + VIEW_MARGIN
            viewport_top = camera.y - VIEW_MARGIN
            viewport_bottom = camera.y + HEIGHT + VIEW_MARGIN
            
            for a in animals:
                # Kiểm tra xem con vật có nằm trong viewport không
                if (viewport_left <= a.pos[0] <= viewport_right and 
                    viewport_top <= a.pos[1] <= viewport_bottom):
                    a.update(dt, player)
                
                for p in placed_items:
                    if p.kind == "bẫy thú" and distance(a.pos, p.pos) < 30:
                        a.hp -= 50
                        placed_items.remove(p)
                        show_msg("Một sinh vật đã sập bẫy protein!")
                        if a.hp <= 0 and a in animals:
                            quest_system.stats[a.kind] += 1
                            drops.append(Drop(a.pos, "thịt thú", random.randint(2, 4)))
                            animals.remove(a)
                        break
            near_campfire = False
            for p in placed_items[:]:
                if p.kind == "lửa trại":
                    p.timer -= dt
                    if distance(player.pos, p.pos) < 150:
                        near_campfire = True
                    if p.timer <= 0: placed_items.remove(p)
            
            # --- CƠ CHẾ LÀM DỊU HÀNH TINH VÀ TÂM TRÍ ---
            if near_campfire:
                # Lửa trại giúp bình tĩnh lại, hồi Sanity và làm Hành tinh quên mày đi nhanh hơn
                player.sanity = min(player.max_sanity, player.sanity + 10.0 * dt)
                planet_awareness = max(0.0, planet_awareness - 5.0 * dt)
            else:
                # Nếu không có lửa, điểm nhận thức vẫn tự nguội đi từ từ
                planet_awareness = max(0.0, planet_awareness - 0.5 * dt)

    # === DRAWING ===
    if game_state == "MENU":
        draw_menu()
        
    elif game_state == "INTRO":
        screen.fill(get_bg_color(0))
        # Draw background tissue pulses
        for i in range(10):
            pygame.draw.circle(screen, (30, 15, 20), (int((i*200 - intro_timer*500)%WIDTH), int((i*150)%HEIGHT)), 50)
            
        ship_key = "flesh_pod" if spaceship_type == "Trực Thăng Trinh Sát" else "nerve_cruiser"
        if ship_key in SPRITES and SPRITES[ship_key]:
            scale = 2.5 - (intro_timer / 4.0)
            img = pygame.transform.scale(SPRITES[ship_key], (int(100*scale), int(100*scale)))
            img = pygame.transform.rotate(img, 180 + math.sin(intro_timer*15)*8)
            screen.blit(img, (intro_pos[0] - img.get_width()//2, intro_pos[1] - img.get_height()//2))
            
            # Thruster Fire
            for _ in range(5):
                fx = intro_pos[0] + random.randint(-20, 20)
                fy = intro_pos[1] - 40 * scale
                pygame.draw.circle(screen, (255, 100, 50), (int(fx), int(fy)), random.randint(10, 25))
            
        # UI Dialogue overlay
        try: msg = intro_msg
        except: msg = "..."
        txt = title_font.render(msg, True, (255, 100, 100))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT - 150))
        
        if intro_timer < 0.8:
            shake = random.randint(-40, 40)
            screen.blit(screen.copy(), (shake, shake))
            # Vẽ hiệu ứng nổ lan tỏa
            expl_radius = int((0.8 - intro_timer) * 1500)
            pygame.draw.circle(screen, (255, 200, 100), (intro_pos[0], intro_pos[1]), expl_radius, 20)
            if intro_timer < 0.2:
                screen.fill((255, 255, 255)) # Flash trắng cuối cùng

    elif game_state == "DNA_MENU":
        screen.fill((10, 0, 10))
        title = title_font.render("HẤP THỤ GENE - ĐỘT BIẾN", True, (200, 50, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        for i, rect in enumerate(dna_rects):
            if i < len(dna_options):
                pygame.draw.rect(screen, (50, 10, 50), rect, border_radius=5)
                pygame.draw.rect(screen, (200, 50, 255), rect, 2, border_radius=5)
                txt = font.render(dna_options[i][0], True, (255, 200, 255))
                screen.blit(txt, (rect.x + 20, rect.y + 15))

    elif game_state == "SPACE":
        screen.fill((5, 0, 10))
        for bh in blackholes: bh.draw(screen, space_camera)
        for ast in asteroids: ast.draw(screen, space_camera)
        for b in space_bullets: b.draw(screen, space_camera)
        space_ship.draw(screen, space_camera)
        screen.blit(font.render(f"GIÁP TÀU: {int(space_ship.hp)}/{space_ship.max_hp} | TÂM TRÍ: {int(sanity)}%", True, (255, 255, 255)), (20, 20))
        screen.blit(small_font.render("BẦU TRỜI RỪNG SÂU - PHÍM MŨI TÊN lái | SPACE bắn | ESC trở về", True, (255, 255, 255)), (20, 50))

        # --- SPACE MINIMAP ---
        mm_w, mm_h = 200, 200
        mm_x, mm_y = WIDTH - mm_w - 20, HEIGHT - mm_h - 20
        mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        mm_surf.fill((10, 5, 20, 180))
        pygame.draw.rect(mm_surf, (100, 100, 255, 255), (0, 0, mm_w, mm_h), 2)
        
        # Ti le: world space -8000 den 8000 -> 16000px
        # Map: 200px
        sc = 200 / 16000
        for ast in asteroids:
            ax, ay = (ast.pos[0] + 8000) * sc, (ast.pos[1] + 8000) * sc
            if 0 <= ax < 200 and 0 <= ay < 200:
                pygame.draw.circle(mm_surf, (150, 150, 150), (int(ax), int(ay)), 2)
        for bh in blackholes:
            bx, by = (bh.pos[0] + 8000) * sc, (bh.pos[1] + 8000) * sc
            if 0 <= bx < 200 and 0 <= by < 200:
                pygame.draw.circle(mm_surf, (255, 0, 255), (int(bx), int(by)), 3)
        # Tau cua ban
        px, py = (space_ship.pos[0] + 8000) * sc, (space_ship.pos[1] + 8000) * sc
        if 0 <= px < 200 and 0 <= py < 200:
            pygame.draw.rect(mm_surf, (255, 255, 255), (px-2, py-2, 4, 4))
        
        screen.blit(mm_surf, (mm_x, mm_y))
        screen.blit(small_font.render("SPACE RADAR", True, (200, 200, 255)), (mm_x, mm_y - 20))

    elif game_state == "SURVIVAL":
        shake_x, shake_y = 0, 0
        
        temp_surface = pygame.Surface((WIDTH, HEIGHT))
        
        # Lấy màu nền theo tầng và thêm hiệu ứng co bóp (Pulse)
        bg_col = get_bg_color(player.pos[1])
        if player.pos[1] > LAYERS["INFECTED"][0]:
            pulse = math.sin(time_tick * 2.5) * 8
            bg_col = (max(0, min(255, bg_col[0] + int(pulse))), bg_col[1], bg_col[2])
        temp_surface.fill(bg_col)
        
        # Background Layers (Chỉ hiện ở tầng SURFACE, dùng chung với Tilemap Bề mặt)
        if player.pos[1] < LAYERS["SURFACE"][1] and "bg1" in SPRITES:
            for bg_key in ["bg1", "bg2", "bg3"]:
                if bg_key not in SPRITES: continue
                bg = SPRITES[bg_key]
                bw, bh = bg.get_width(), bg.get_height()
                parallax = 1.0 if bg_key == "bg1" else 0.8 if bg_key == "bg2" else 0.6
                ox, oy = -(camera.x * parallax) % bw, -(camera.y * parallax) % bh
                for x in range(int(ox - bw), int(WIDTH), int(bw)):
                    for y in range(int(oy - bh), int(HEIGHT), int(bh)):
                        temp_surface.blit(bg, (x, y))
        
        # --- DRAW TILEMAP (CULLING) ---
        # Chỉ lặp và vẽ những ô nằm trong khung hình camera
        start_col = max(0, int(camera.x // TILE_SIZE))
        end_col = min(len(map_data[0]), int((camera.x + WIDTH) // TILE_SIZE) + 1)
        start_row = max(0, int(camera.y // TILE_SIZE))
        end_row = min(len(map_data), int((camera.y + HEIGHT) // TILE_SIZE) + 1)
        
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile = map_data[row][col]
                tx = int(col * TILE_SIZE - camera.x)
                ty = int(row * TILE_SIZE - camera.y)
                
                if tile == 1:
                    # Ve tuong (Wall) thanh cay thay vi hinh vuong
                    if "item_cay" in SPRITES and SPRITES["item_cay"]:
                        if "wall_cay" not in SPRITES:
                            # Scale to cover the tile completely, slightly larger to overlap
                            SPRITES["wall_cay"] = pygame.transform.scale(SPRITES["item_cay"], (TILE_SIZE + 20, TILE_SIZE + 20))
                        temp_surface.blit(SPRITES["wall_cay"], (tx - 10, ty - 15))
                    else:
                        wall_col = get_bg_color(row * TILE_SIZE)
                        wall_col = (max(0, wall_col[0]-15), max(0, wall_col[1]-15), max(0, wall_col[2]-15))
                        pygame.draw.rect(temp_surface, wall_col, (tx, ty, TILE_SIZE, TILE_SIZE))
                elif tile == 0:
                    # Nen dat trong, khong ve checkerboard nua
                    pass

        for dec in decorations: dec.draw(temp_surface, camera)
        for r in resources: r.draw(temp_surface, camera)
        for p in placed_items: p.draw(temp_surface, camera)
        for d in drops: d.draw(temp_surface, camera)
        for a in animals: a.draw(temp_surface, camera)
        storage_obj.draw(temp_surface, camera)  # Ve kho do
        sx, sy = camera.apply(landed_ship_pos)
        ship_key = "flesh_pod" if spaceship_type == "Trực Thăng Trinh Sát" else "nerve_cruiser"
        if ship_key in SPRITES and SPRITES[ship_key]:
            ship_sprite = pygame.transform.scale(SPRITES[ship_key], (120, 120))
            if not ship_repaired:
                # Vẽ tàu bị hỏng (ám đen và xoay nghiêng)
                ship_sprite = pygame.transform.rotate(ship_sprite, 45)
                ship_sprite.fill((50, 50, 50, 150), special_flags=pygame.BLEND_RGBA_MULT)
                temp_surface.blit(ship_sprite, (sx - 60, sy - 60))
                # Hien thong bao sua tau neu dung gan
                dist_to_ship = distance(player.pos, landed_ship_pos)
                if dist_to_ship < 160:
                    inv = player.inventory
                    can_repair = (inv.get("nấm linh chi", 0) >= 10 and inv.get("dược thảo", 0) >= 10 and 
                                  inv.get("da thú giáp", 0) >= 5 and inv.get("nhựa cây độc", 0) >= 5)
                    txt = "Ấn [P] để SỬA TÀU" if can_repair else "Thiếu nguyên liệu để sửa tàu!"
                    col = (255, 255, 100) if can_repair else (255, 100, 100)
                    hint = small_font.render(txt, True, col)
                    temp_surface.blit(hint, (sx - hint.get_width()//2, sy + 70))
            else:
                temp_surface.blit(ship_sprite, (sx - 60, sy - 60))
                if distance(player.pos, landed_ship_pos) < 160:
                    hint = small_font.render("Ấn [P] để CẤT CÁNH", True, (100, 255, 100))
                    temp_surface.blit(hint, (sx - hint.get_width()//2, sy + 70))
        player.draw(temp_surface, camera)
        screen.blit(temp_surface, (shake_x, shake_y))
        
        # --- FOG OF WAR (Depth based) ---
        # Tăng dần độ tối theo độ sâu, ở tầng cuối cùng sẽ tối thui (255)
        depth_fog_alpha = min(255, int((player.pos[1] / MAP_H) * 235) + 20)
        
        ui_fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ui_fog.fill((0, 0, 0, depth_fog_alpha))
        
        # Tinh toan tam nhin - Gan nhu khong thay gi neu khong co duoc
        has_torch = player.inventory.get("đuốc", 0) > 0
        light_radius = 450 if has_torch else 30 # Chi thay sat chan neu khong co duoc
            
        # Ve lo thung vao fog
        pygame.draw.circle(ui_fog, (0, 0, 0, 0), (WIDTH//2, HEIGHT//2), light_radius)
        # Soft edges (Quầng sáng)
        fade_size = 15 if not has_torch else 100
        for r in range(max(0, light_radius - fade_size), light_radius, 5):
            alpha = int(depth_fog_alpha * (1 - (light_radius - r) / fade_size))
            pygame.draw.circle(ui_fog, (0, 0, 0, alpha), (WIDTH//2, HEIGHT//2), r, 2)
            
        screen.blit(ui_fog, (0, 0))
        
        # UI bars
        draw_bar(screen, 20, 20, 200, 18, player.hp, player.max_hp, (220, 50, 50), "HP")
        draw_bar(screen, 20, 45, 200, 18, player.hunger, player.max_hunger, (200, 150, 50), "Năng lượng")
        draw_bar(screen, 20, 70, 200, 18, player.thirst, player.max_thirst, (50, 150, 220), "Nước suối")
        draw_bar(screen, 20, 95, 200, 18, player.stamina, player.max_stamina, (50, 200, 100), "Thể lực")
        draw_bar(screen, 20, 120, 200, 18, player.sanity, player.max_sanity, (100, 200, 255), "Tinh thần")
        
        # --- QUEST PANEL (TOP CENTER) - Toggle bang Tab ---
        obj_text, obj_done = quest_system.get_objective(player)
        quest_col = (100, 255, 100) if obj_done else (255, 200, 50)
        if show_quest:
            # Drop guide rows
            drop_guide = [
                ("Slime Bùn Bùn",           (180, 80, 80),   "→ Thịt thú, Nấm linh chi"),
                ("Yêu Tinh Rừng", (220, 100, 50),  "→ Thịt thú, Nấm, Da thú, Dược thảo, Nhựa độc(ít)"),
                ("Quái Vật Bóng Đêm",      (120, 80, 220),  "→ Thịt thú, Nấm linh chi, Nhựa cây độc"),
                ("Sợi Gỗ sồi",    (80, 160, 80),   "→ Gỗ sồi  (từ nguồn tài nguyên)"),
                ("Suối Nước",  (60, 120, 200),  "→ Nước suối  (từ nguồn tài nguyên)"),
            ]
            drop_h = len(drop_guide) * 19 + 26
            # Wrap quest title
            max_w = 660
            words = obj_text.split(' ')
            lines_wrap = []; cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if small_font.size(test)[0] <= max_w:
                    cur = test
                else:
                    if cur: lines_wrap.append(cur)
                    cur = w
            if cur: lines_wrap.append(cur)
            n_lines = len(lines_wrap)
            detail_h = 90 if not ship_repaired else 0
            panel_h = 20 + n_lines * 22 + 8 + detail_h + drop_h
            quest_bg_rect = pygame.Rect(WIDTH//2 - 350, 8, 700, panel_h)
            panel_surf = pygame.Surface((quest_bg_rect.w, quest_bg_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(panel_surf, (20, 20, 30, 215), (0, 0, quest_bg_rect.w, quest_bg_rect.h), border_radius=8)
            pygame.draw.rect(panel_surf, (150, 150, 200, 255), (0, 0, quest_bg_rect.w, quest_bg_rect.h), 2, border_radius=8)
            screen.blit(panel_surf, (quest_bg_rect.x, quest_bg_rect.y))
            # Quest title (wrapped)
            for li, ln in enumerate(lines_wrap):
                q_txt = small_font.render(ln, True, quest_col)
                screen.blit(q_txt, (WIDTH//2 - q_txt.get_width()//2, 18 + li * 22))
            # Material progress (khi chua repair)
            base_y = 18 + n_lines * 22 + 4
            if not ship_repaired:
                q_info = [
                    f"- Nấm linh chi: {player.inventory.get('nấm linh chi', 0)}/10",
                    f"- Dược thảo: {player.inventory.get('dược thảo', 0)}/10",
                    f"- Da thú giáp: {player.inventory.get('da thú giáp', 0)}/5",
                    f"- Nhựa cây độc: {player.inventory.get('nhựa cây độc', 0)}/5",
                    "→ NHẤN [P] ĐỂ SỬA TÀU (KHI ĐỨNG GẦN TÀU)"
                ]
                for gi, gline in enumerate(q_info):
                    color = (200, 220, 255) if gi < 4 else (255, 255, 100)
                    screen.blit(small_font.render(gline, True, color), (WIDTH//2 - 300, base_y + gi*20))
                base_y += detail_h
            # --- Drop Guide ---
            pygame.draw.line(screen, (100, 100, 150),
                             (quest_bg_rect.x + 15, base_y + 5),
                             (quest_bg_rect.x + quest_bg_rect.w - 15, base_y + 5), 1)
            screen.blit(small_font.render("DROP GUIDE:", True, (180, 180, 255)), (quest_bg_rect.x + 18, base_y + 8))
            for di, (mob, mcol, drop_txt) in enumerate(drop_guide):
                dy = base_y + 27 + di * 19
                screen.blit(small_font.render(f"  {mob}:", True, mcol),        (quest_bg_rect.x + 18, dy))
                screen.blit(small_font.render(drop_txt, True, (200, 230, 200)), (quest_bg_rect.x + 220, dy))
        else:
            # Chi hien 1 dong nho o tren khi an
            short = obj_text if len(obj_text) <= 70 else obj_text[:67] + "..."
            q_mini = small_font.render(f"[Tab] {short}", True, quest_col)
            screen.blit(q_mini, (WIDTH//2 - q_mini.get_width()//2, 5))
        
        

        # --- BALO (BACKPACK PANEL) - Bottom Left, nho gon ---
        bp_w, bp_h = 190, 220
        bp_x, bp_y = 10, HEIGHT - bp_h - 40
        bp_surf = pygame.Surface((bp_w, bp_h), pygame.SRCALPHA)
        pygame.draw.rect(bp_surf, (15, 10, 25, 195), (0, 0, bp_w, bp_h), border_radius=8)
        pygame.draw.rect(bp_surf, (180, 140, 50, 255), (0, 0, bp_w, bp_h), 2, border_radius=8)
        screen.blit(bp_surf, (bp_x, bp_y))
        if "icon_backpack" in SPRITES:
            screen.blit(pygame.transform.scale(SPRITES["icon_backpack"], (18, 18)), (bp_x+5, bp_y+5))
        screen.blit(small_font.render("BALO (B:Kho)", True, (255, 220, 100)), (bp_x+27, bp_y+7))
        item_icon_map = {
            "nấm linh chi":"icon_nam_linh_chi", "dược thảo":"icon_duoc_thao",
            "thịt thú":"icon_thit_thu", "gỗ sồi":"icon_go_soi",
            "nhựa cây độc":"icon_nhua_cay_doc", "da thú giáp":"icon_da_thu",
            "nước suối":"icon_nuoc_suoi",
            "dao găm":"icon_dao_gam", "kiếm gỗ":"icon_kiem_go",
            "vũ khí cường hóa":"icon_kiem_cuong_hoa",
            "áo choàng lá":"icon_ao_choang_la", "giáp da":"icon_giap_da",
            "bùa rừng sâu":"icon_bua_rung_sau",
            "mặt nạ phòng độc":"icon_mat_na_phong_doc", "bùa hộ mệnh":"icon_bua_ho_menh",
            "thảo dược giải độc":"icon_thao_duoc_giai_doc", "giáp cổ đại":"icon_giap_co_dai",
            "bẫy thú":"icon_potion", "lửa trại":"icon_shield", "đuốc":"icon_torch",
        }
        iy = bp_y + 26
        for k, v in player.inventory.items():
            if v > 0 and iy < bp_y + bp_h - 8:
                ik = item_icon_map.get(k)
                if ik and ik in SPRITES:
                    screen.blit(pygame.transform.scale(SPRITES[ik], (16, 16)), (bp_x+5, iy+1))
                col = (100,255,200) if "dao găm" in k else \
                      (255,180,100) if "giáp" in k else \
                      (200,255,200) if k in {"mặt nạ phòng độc","bùa hộ mệnh","thảo dược giải độc","giáp cổ đại"} else \
                      (200,200,200)
                screen.blit(small_font.render(f"{k}: {v}", True, col), (bp_x+25, iy+2))
                iy += 19
        

        # --- HINTS BAR (BOTTOM) ---
        hint_text = "Mũi tên:Di chuyển | SHIFT:Chạy | F/E:Đánh/Nhặt | P:Tàu | C:Chế tạo | SPACE:Đặt Bẫy/Lửa trại | Q/W:Ăn/Uống | B:Kho | TAB:Nhiệm vụ"
        h_surf = small_font.render(hint_text, True, (200, 220, 255))
        
        bar_h = 30
        bar_rect = pygame.Rect(0, HEIGHT - bar_h, WIDTH, bar_h)
        bar_bg = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(bar_bg, (20, 20, 30, 200), (0, 0, bar_rect.w, bar_rect.h))
        screen.blit(bar_bg, (bar_rect.x, bar_rect.y))
        screen.blit(h_surf, (WIDTH//2 - h_surf.get_width()//2, HEIGHT - bar_h + 6))
        
        # --- MINIMAP (BOTTOM RIGHT) ---
        mm_w, mm_h = 150, 150
        mm_x, mm_y = WIDTH - mm_w - 20, HEIGHT - mm_h - 40
        minimap_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        minimap_surf.fill((20, 10, 15, 180))
        pygame.draw.rect(minimap_surf, (200, 50, 50), (0, 0, mm_w, mm_h), 2)
        scale_x, scale_y = mm_w / MAP_W, mm_h / MAP_H
        # Tau (magenta)
        pygame.draw.circle(minimap_surf, (255, 100, 255), (int(landed_ship_pos[0]*scale_x), int(landed_ship_pos[1]*scale_y)), 4)
        # Kho do (vang) - danh dau hinh vuong
        sx = int(storage_obj.pos[0]*scale_x)
        sy = int(storage_obj.pos[1]*scale_y)
        pygame.draw.rect(minimap_surf, (255, 220, 0), (sx-3, sy-3, 6, 6))
        pygame.draw.rect(minimap_surf, (200, 160, 0), (sx-3, sy-3, 6, 6), 1)
        # Quai (do)
        for a in animals: pygame.draw.circle(minimap_surf, (255, 0, 0), (int(a.pos[0]*scale_x), int(a.pos[1]*scale_y)), 2)
        # Nguoi choi (xanh la)
        pygame.draw.circle(minimap_surf, (0, 255, 0), (int(player.pos[0]*scale_x), int(player.pos[1]*scale_y)), 3)
        screen.blit(minimap_surf, (mm_x, mm_y))
        # Chu thich minimap
        screen.blit(small_font.render("[Xanh=Bạn] [Vàng=Kho] [Tím=Tàu]", True, (150,150,150)), (mm_x, mm_y - 13))

        # --- MESSAGES LOG (BOTTOM CENTER) ---
        my = HEIGHT - 100
        for m in messages[:]:
            m["time"] -= dt
            if m["time"] <= 0: messages.remove(m)
            else:
                txt = small_font.render(m["text"], True, (255, 255, 255))
                # Shadow/Outline
                shadow = small_font.render(m["text"], True, (0, 0, 0))
                
                # Nền mờ cho message
                msg_bg = pygame.Surface((txt.get_width() + 20, txt.get_height() + 4), pygame.SRCALPHA)
                pygame.draw.rect(msg_bg, (0, 0, 0, 150), (0, 0, txt.get_width() + 20, txt.get_height() + 4), border_radius=5)
                
                screen.blit(msg_bg, (WIDTH//2 - txt.get_width()//2 - 10, my - 2))
                screen.blit(shadow, (WIDTH//2 - txt.get_width()//2 + 1, my + 1))
                screen.blit(txt, (WIDTH//2 - txt.get_width()//2, my))
                my -= 25

        # Hiệu ứng Tâm trí thấp: lớp đỏ bao phủ màn hình
        if player.sanity < 50:
            alpha = int((50 - player.sanity) / 50 * 160)  # 0 → 160 alpha
            sanity_vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            sanity_vignette.fill((180, 0, 0, alpha))
            screen.blit(sanity_vignette, (0, 0))

        # --- MENU CHẾ TẠO (CRAFTING) ---
        if show_crafting and not show_storage:
            craft_w, craft_h = 560, 430
            craft_x, craft_y = WIDTH//2 - craft_w//2, HEIGHT//2 - craft_h//2
            craft_surf = pygame.Surface((craft_w, craft_h), pygame.SRCALPHA)
            pygame.draw.rect(craft_surf, (15, 15, 25, 245), (0, 0, craft_w, craft_h), border_radius=10)
            pygame.draw.rect(craft_surf, (200, 200, 100, 255), (0, 0, craft_w, craft_h), 2, border_radius=10)
            screen.blit(craft_surf, (craft_x, craft_y))
            title = small_font.render("=== CHẾ TẠO (C: Đóng) ===", True, (255, 255, 100))
            screen.blit(title, (craft_x + craft_w//2 - title.get_width()//2, craft_y + 10))
            # Duong ke
            pygame.draw.line(screen, (100, 100, 60), (craft_x+10, craft_y+30), (craft_x+craft_w-10, craft_y+30), 1)
            recipes_display = [
                ("1", "Lửa trại", "3 Gỗ sồi + 2 Nấm linh chi",          (150,255,150)),
                ("2", "Bẫy thú",      "2 Gỗ sồi + 5 Nấm linh chi",          (150,255,150)),
                ("3", "Đuốc",         "TẦM NHÌN | 2 Gỗ sồi + 1 Nhựa",       (255,255,100)),
                ("4", "Dao găm",         "+25 DMG | 5 Gỗ sồi + 10 Nấm",   (100,200,255)),
                ("5", "Kiếm gỗ",  "+40 DMG | 10 Gỗ sồi + 5 Dược thảo",  (100,200,255)),
                ("6", "Vũ khí cường hóa",   "+70 DMG | 10 Nhựa + 10 Dược thảo", (100,200,255)),
                ("7", "Áo choàng lá",        "+100 HP | 8 Gỗ sồi + 10 Dược thảo",  (255,160, 80)),
                ("8", "Giáp da", "+200 HP | 10 Nước suối + 10 Da thú",      (255,160, 80)),
                ("9", "Bùa rừng sâu",    "+350 HP | 15 Nhựa + 15 Da thú",      (255,160, 80)),
                ("0", "Mặt nạ phòng độc",      "Vào RỪNG GIÀ | 10 Gỗ sồi + 8 Nấm",  (100,255,200)),
                ("-", "Bùa hộ mệnh",         "Vào ĐẦM LẦY ĐỘC  | 15 Dược thảo + 10 Da thú",    (100,255,200)),
                ("=", "Thảo dược giải độc",    "Vào THUNG LŨNG SƯƠNG MÙ  | 12 Nước suối + 12 Da thú",     (200,150,255)),
                ("L", "Giáp cổ đại",         "Vào LÕI RỪNG | 20 Nhựa + 20 Da giáp + 15 Dược", (255,100,100)),
            ]
            cy = craft_y + 38
            for num, name, cost, col in recipes_display:
                # Xac dinh co du nguyen lieu khong
                row_col = col
                screen.blit(small_font.render(f"[{num}] {name:<22} {cost}", True, row_col), (craft_x + 18, cy))
                cy += 30
            close_hint = small_font.render("B: Mở Kho  |  C: Đóng", True, (150,150,150))
            screen.blit(close_hint, (craft_x + craft_w//2 - close_hint.get_width()//2, craft_y + craft_h - 22))
    pygame.display.flip()

pygame.quit()
