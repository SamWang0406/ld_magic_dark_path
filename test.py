import easyocr

reader = easyocr.Reader(['ch_tra'])
result = reader.readtext('image.png', detail=0)
print(result)
