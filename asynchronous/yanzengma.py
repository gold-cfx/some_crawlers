from io import BytesIO

import requests
from PIL import Image, ImageFilter
from pytesseract import image_to_string


def main():
    resp  = requests.get('http://www.yundama.com/index/captcha?r=0.018109785648503074')
    img1 = Image.open(BytesIO(resp.content))
    img1.save('yanzhengma1.jpg')
    img2 = Image.open(open('yanzhengma1.jpg', 'rb'))
    img3 = img2.point(lambda x: 0 if x < 128 else 255)
    img3.save(open('yanzhengma100.jpg', 'wb'))
    print(image_to_string(img3))


if __name__ == '__main__':
    main()