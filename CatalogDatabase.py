import cv2
import numpy as np
from PIL import Image
import pytesseract
from wand.image import Image as wi
import sqlite3
from wand.color import Color
import string


conn = sqlite3.connect("CatalogDatabase.db")
cursor = conn.cursor()


def create_table():
    cursor.execute("CREATE TABLE IF NOT EXISTS Catalog (Item TEXT, Store TEXT, Month TEXT, Page INT, Image TEXT)")

create_table()

def preprocessing_for_gratis(image):
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    eroded = cv2.erode(gray_img, (2, 1), iterations=1)
    blur_otsu = cv2.GaussianBlur(eroded, (3, 3), 5)
    ret1, otsu_threshold = cv2.threshold(blur_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur_adaptive = cv2.GaussianBlur(eroded, (7, 7), 0)
    adaptive_threshold = cv2.adaptiveThreshold(blur_adaptive, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                                               13, 5)
    or_image = cv2.bitwise_or(otsu_threshold, adaptive_threshold)
    return or_image


def preprocessing_for_rossmann(image):
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary_threshold = cv2.threshold(gray_img, 120, 255, cv2.THRESH_BINARY)
    bil_blur = cv2.bilateralFilter(adaptive_thresholding, 3, 155, 155)
    return bil_blur


def preprocessing_for_watsons(image):
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bil_blur = cv2.bilateralFilter(gray_img, 3, 95, 95)
    ret1, binary_threshold = cv2.threshold(bil_blur, 130, 255, cv2.THRESH_BINARY)
    return binary_threshold


def text_detect_for_rossmann_watsons(img, element_size=(35, 35)):
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret1, threshold1 = cv2.threshold(img,50, 255, cv2.THRESH_BINARY)
    ret2, threshold2 = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold2_adaptive = cv2.adaptiveThreshold(threshold2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 155)
    or_image_text_detect = cv2.bitwise_or(threshold1, threshold2_adaptive)
    img_sobel = cv2.Sobel(or_image_text_detect, cv2.CV_8U, 1,0)
    element = cv2.getStructuringElement(cv2.MORPH_RECT, element_size)
    img_closed = cv2.morphologyEx(img_sobel, cv2.MORPH_CLOSE, element)
    contours, hierarchy = cv2.findContours(img_closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    Rect = [cv2.boundingRect(i) for i in contours if i.shape[0] > 250]
    Rect_Extended = [(int(i[0] - i[2] * 0.06), int(i[1] - i[3] * 0.06), int(i[0] + i[2] * 1.06), int(i[1] + i[3] * 1.06)) for i in
             Rect]
    return Rect_Extended


def text_detect_for_gratis(img, element_size=(55, 55)):
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret1, threshold1 = cv2.threshold(img,50, 255, cv2.THRESH_BINARY)
    ret2, threshold2 = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold2_adaptive = cv2.adaptiveThreshold(threshold2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 155)
    or_image_text_detect = cv2.bitwise_or(threshold1, threshold2_adaptive)
    img_sobel = cv2.Sobel(or_image_text_detect, cv2.CV_8U, 1,0)
    element = cv2.getStructuringElement(cv2.MORPH_RECT, element_size)
    img_closed = cv2.morphologyEx(img_sobel, cv2.MORPH_CLOSE, element)
    contours, hierarchy = cv2.findContours(img_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    Rect = [cv2.boundingRect(i) for i in contours if i.shape[0] > 450]
    Rect_Extended = [(int(i[0] - i[2] * 0.06), int(i[1] - i[3] * 0.06), int(i[0] + i[2] * 1.06), int(i[1] + i[3] * 1.06)) for i in
             Rect]
    return Rect_Extended


def main():
    store = input("The catalog is valid in store: ")
    if store.lower() == 'gratis' or store.lower() =='rossmann' or store.lower() == 'watsons':
        input_pdf = input("Please input pdf file path: ")
        month = input("The catalog is valid in month: ")
        all_pages = wi(filename=input_pdf, resolution=300)
        for j, page in enumerate(all_pages.sequence):
             with wi(page) as img:
                img.format = 'png'
                page_num = j+1
                output_page_filename = (input_pdf.split(".")[0] + str(page_num) + '.png')
                img.save(filename=output_page_filename)
                page_image = cv2.imread(output_page_filename)
                if store.lower() == 'gratis':
                    rectp = text_detect_for_gratis(page_image)
                    for i in rectp:
                        cv2.rectangle(page_image, i[:2], i[2:], (0, 0, 255))
                        cropped = page_image[i[1]:i[3], i[0]:i[2]]
                        processed_image = preprocessing_for_gratis(cropped)

                            cursor.execute("INSERT INTO Catalog (Item, Store, Month, Page, Image) VALUES (?,?,?,?,?)",
                                           (product, store.lower(), month.lower(), page_num, output_page_filename))
                            conn.commit()
                elif store.lower() == 'rossmann':
                    rectp = text_detect_for_rossmann_watsons(page_image)
                    for i in rectp:
                        cv2.rectangle(page_image, i[:2], i[2:], (0, 0, 255))
                        cropped = page_image[i[1]:i[3], i[0]:i[2]]
                        processed_image = preprocessing_for_rossmann(cropped)
                        product = pytesseract.image_to_string(Image.fromarray(processed_image, mode = None), lang='tur')
                        if len(product) > 10 and len(product) < 150:
                            cursor.execute("INSERT INTO Catalog (Item, Store, Month, Page, Image) VALUES (?,?,?,?,?)",
                                           (product, store, month, page_num, output_page_filename))
                            conn.commit()
                elif store.lower() == 'watsons':
                    rectp = text_detect_for_rossmann_watsons(page_image)
                    for i in rectp:
                        cv2.rectangle(page_image, i[:2], i[2:], (0, 0, 255))
                        cropped = page_image[i[1]:i[3], i[0]:i[2]]
                        processed_image = preprocessing_for_watsons(cropped)
                        product = pytesseract.image_to_string(Image.fromarray(processed_image, mode = None), lang='tur')
                        if len(product) > 10 and len(product) < 150:
                            cursor.execute("INSERT INTO Catalog (Item, Store, Month, Page, Image) VALUES (?,?,?,?,?)",
                                           (product, store, month, page_num, output_page_filename))
                            conn.commit()
    else:
        print("This store is not available yet...")
        return 0
    return img


main()




