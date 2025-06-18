import os, re, sys
from PIL import Image

PPI = 300

def crop_and_resize(input_path, length, height, x_start, x_end, y_start, y_end, output_base_folder):
    image = Image.open(input_path).convert("RGBA")
    w_px, h_px = image.size
    pps = w_px / length if length else h_px / height
    left, right = (x_start - 1) * pps, x_end * pps
    top, bottom = (y_start - 1) * pps, y_end * pps
    cropped = image.crop((left, top, right, bottom))
    squares_x, squares_y = x_end - x_start + 1, y_end - y_start + 1
    resized = cropped.resize((int(squares_x * PPI), int(squares_y * PPI)), Image.LANCZOS)
    output_folder = build_output_folder(input_path, output_base_folder)
    os.makedirs(output_folder, exist_ok=True)
    file_number = get_next_file_number(output_folder)
    output_path = os.path.join(output_folder, f"{file_number}.png")
    resized.save(output_path, PPI=(PPI, PPI))
    return output_path, squares_x, squares_y

def build_output_folder(input_path, output_base_folder):
    input_path = os.path.normpath(input_path)
    relative = input_path.removeprefix('input' + os.sep).removeprefix('input/')
    dir_part = os.path.splitext(relative)[0]
    return os.path.join(output_base_folder, dir_part)

def get_next_file_number(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.png') and f[:-4].isdigit()]
    numbers = [int(f[:-4]) for f in files]
    return max(numbers)+1 if numbers else 1

def parse_header_line(line):
    m = re.match(r"""(['"])(.*?)\1\s+([lhLH])\s+([\d\.]+)""", line)
    if not m: raise ValueError(f"nome do arquivo inválido: {line}")
    return m.group(2), m.group(3).lower(), float(m.group(4))

def apply_grid(img, grid_path, squares_x, squares_y):
    if not os.path.exists(grid_path):
        return img
    max_w, max_h = 8, 11
    img_w, img_h = int(squares_x * PPI), int(squares_y * PPI)
    grid = Image.open(grid_path).convert("RGBA")
    if squares_x > max_w:
        grid = grid.rotate(90, expand=True)
        max_w, max_h = max_h, max_w
    if squares_y > max_h:
        raise ValueError("a imagem não cabe na folha A4")
    grid = grid.resize((max_w * PPI, max_h * PPI), Image.LANCZOS)
    grid_cropped = grid.crop((0, 0, img_w, img_h))
    return Image.alpha_composite(img, grid_cropped)

def create_a4_with_image(img, output_path):
    a4_w, a4_h = int(8.27 * PPI), int(11.69 * PPI)
    w, h = img.size
    if w <= a4_w and h <= a4_h:
        final_img = img
        pos = ((a4_w - w)//2, (a4_h - h)//2)
    elif h <= a4_w and w <= a4_h:
        final_img = img.rotate(90, expand=True)
        pos = ((a4_w - final_img.width)//2, (a4_h - final_img.height)//2)
    else:
        raise ValueError("a imagem não cabe na folha A4")
    a4 = Image.new('RGB', (a4_w, a4_h), 'white')
    a4.paste(final_img.convert("RGB"), pos)
    a4.save(output_path, PPI=(PPI, PPI))

def process_txt(file_path, output_folder, print_mode=False, grid_mode=False):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    current_image = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('#','//',';','--')):
            current_image = None
            continue
        if current_image is None:
            try:
                img_name, mode, squares = parse_header_line(line)
                current_image = os.path.join('input', img_name)
                if mode not in ('l','h'): current_image = None
            except:
                current_image = None
        else:
            parts = line.split()
            if len(parts) != 4: continue
            try:
                x_start, x_end, y_start, y_end = map(float, parts)
                length, height = (squares, None) if mode == 'l' else (None, squares)
                out_path, sx, sy = crop_and_resize(current_image, length, height, x_start, x_end, y_start, y_end, output_folder)
                img = Image.open(out_path).convert("RGBA")
                base = out_path.removesuffix('.png')
                if grid_mode:
                    grid_path = 'grid.png'
                    if x_start % 1 != 0 and y_start % 1 == 0:
                        grid_path = 'gridx.png'
                    elif x_start % 1 == 0 and y_start % 1 != 0:
                        grid_path = 'gridy.png'
                    elif x_start % 1 != 0 and y_start % 1 != 0:
                        grid_path = 'gridxy.png'
                    img_with_grid = apply_grid(img, "./assets/"+grid_path, sx, sy)
                    img_with_grid.save(f"{base}_grid.png", PPI=(PPI, PPI))
                else:
                    img_with_grid = img
                if print_mode:
                    suffix = '_grid_print' if grid_mode else '_print'
                    create_a4_with_image(img_with_grid, f"{base}{suffix}.png")
            except:
                pass

def make_pdf(folder, grid_mode=False):
    suffix = '_grid_print.png' if grid_mode else '_print.png'
    imgs = [f for f in os.listdir(folder) if f.endswith(suffix)]
    if not imgs:
        return
    imgs.sort()
    paths = [os.path.join(folder, f) for f in imgs]
    imgs_opened = [Image.open(p).convert('RGB') for p in paths]
    first, *rest = imgs_opened
    folder_name = os.path.basename(folder)
    pdf_path = os.path.join(folder, f"{folder_name}.pdf")
    first.save(pdf_path, save_all=True, append_images=rest)

if __name__ == "__main__":
    txt_file, output_folder = 'cuts.txt', 'output'
    print_mode = '--print' in sys.argv
    grid_mode = '--grid' in sys.argv
    pdf_mode = '--pdf' in sys.argv

    process_txt(txt_file, output_folder, print_mode, grid_mode)

    if pdf_mode:
        for root, dirs, files in os.walk(output_folder):
            if not dirs:
                make_pdf(root, grid_mode)
