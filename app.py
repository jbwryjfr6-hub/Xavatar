import os
import zipfile
import tempfile
from flask import Flask, request, render_template, send_file
from wand.image import Image
from wand.drawing import Drawing

app = Flask(__name__)

DDS_SIZES = [64, 128, 260, 440]
PNG_SIZE = 440

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return "لم يتم اختيار صورة", 400
    
    file = request.files['image']
    shape = request.form.get('shape', 'square')
    
    if file.filename == '':
        return "اسم الملف فارغ", 400

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input_image")
        file.save(input_path)
        xavatar_path = os.path.join(tmpdir, "avatar.xavatar")

        try:
            with Image(filename=input_path) as original:
                # قص الصورة لمربع لتجنب التشوه
                orig_w, orig_h = original.width, original.height
                min_dim = min(orig_w, orig_h)
                left = (orig_w - min_dim) // 2
                top = (orig_h - min_dim) // 2
                original.crop(left=left, top=top, width=min_dim, height=min_dim)

                # إنشاء ملفات DDS
                for size in DDS_SIZES:
                    with original.clone() as img:
                        img.resize(size, size, filter='lanczos')
                        
                        # إضافة الشفافية للزوايا إذا اختار المستخدم دائري
                        if shape == 'circle':
                            img.alpha_channel = True
                            with Image(width=size, height=size) as mask:
                                with Drawing() as draw:
                                    draw.fill_color = 'white'
                                    # رسم الدائرة في المنتصف
                                    draw.circle(origin=(size/2, size/2), radius=size/2)
                                    draw(mask)
                                img.composite(mask, 0, 0, operator='copy_alpha')

                        img.compression = 'dxt5'
                        img.format = 'dds'
                        img.save(filename=os.path.join(tmpdir, f"avatar{size}.dds"))

                # إنشاء صورة PNG
                with original.clone() as png_img:
                    png_img.resize(PNG_SIZE, PNG_SIZE, filter='lanczos')
                    if shape == 'circle':
                        png_img.alpha_channel = True
                        with Image(width=PNG_SIZE, height=PNG_SIZE) as mask:
                            with Drawing() as draw:
                                draw.fill_color = 'white'
                                draw.circle(origin=(PNG_SIZE/2, PNG_SIZE/2), radius=PNG_SIZE/2)
                                draw(mask)
                            png_img.composite(mask, 0, 0, operator='copy_alpha')
                    
                    png_img.format = 'png'
                    png_img.save(filename=os.path.join(tmpdir, "avatar.png"))

            # ضغط الملفات في ملف xavatar (وهو عبارة عن zip)
            with zipfile.ZipFile(xavatar_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for size in DDS_SIZES:
                    zf.write(os.path.join(tmpdir, f"avatar{size}.dds"), arcname=f"avatar{size}.dds")
                zf.write(os.path.join(tmpdir, "avatar.png"), arcname="avatar.png")

            # إرسال الملف للمستخدم لتحميله
            return send_file(xavatar_path, as_attachment=True, download_name=f"avatar_{shape}.xavatar")

        except Exception as e:
            return f"حدث خطأ أثناء معالجة الصورة: {str(e)}", 500

if __name__ == '__main__':
    # هذا السطر للتجربة المحلية فقط، المنصة ستشغله بطريقتها
    app.run(host='0.0.0.0', port=5000)
