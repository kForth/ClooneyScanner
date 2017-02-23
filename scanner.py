import math
from os import path, remove

import cv2
import numpy as np

DEBUG_SAVE_IMAGES = False
DEBUG_SHOW_ALL_BOXES = False
DEBUG_SHOW_AFTER_CORNERS = False
SENSITIVITY = 100

NUMBERS_MODEL = [[True, True, True, False, True, True, True],
                 [False, False, True, False, False, True, False],
                 [True, False, True, True, True, False, True],
                 [True, False, True, True, False, True, True],
                 [False, True, True, True, False, True, False],
                 [True, True, False, True, False, True, True],
                 [True, True, False, True, True, True, True],
                 [True, False, True, False, False, True, False],
                 [True, True, True, True, True, True, True],
                 [True, True, True, True, False, True, True]]
ALT_NUMBERS_MODEL = [[False, False, False, False, False, False, False],
                     [False, True, False, False, True, False, False],
                     None,
                     None,
                     None,
                     None,
                     [False, True, False, True, True, True, True],
                     None,
                     None,
                     [True, True, True, True, False, True, False]]

SHEET_WIDTH = 8.5  # 8.375
SHEET_HEIGHT = 11  # 10.875


def dump_sheet_data(event_id, data, headers):
    filename = "./data/" + event_id + "/" + event_id + ".csv"
    dump_str = ""

    for i in range(len(headers)):
        h = headers[i]
        if h not in data.keys():
            dump_str += "0,"
            continue
        else:
            dump_str += str(data[h][0]).encode('ascii', 'ignore') + ","
    dump_str = dump_str[:-1]
    dump_str += "\n"
    open(filename, "a").write(dump_str)
    # try:
    #     all_data = json.load(open("StrongholdData.json"))
    # except:
    #     all_data = {}
    # all_data["m" + str(data["Match"]) + "p" + str(data["Pos"])] = data
    # json.dump(all_data, open("StrongholdData.json", "w"))


def load_field_data():
    f = open("StrongholdFields.csv")
    lines = map(lambda x: x.split(","), f.read().strip().split("\n"))

    return lines[:-1], lines[-1]


def get_shot_locations(im):
    detector = cv2.SimpleBlobDetector()
    keypoints = detector.detect(im)
    cv2.drawKeypoints(im, keypoints, np.array([]), (0, 0, 255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    # Show keypoints
    points = []
    for p in keypoints:
        points.append(p.pt)
    return points


def avg_value(img):
    s = 0
    for r in img:
        for c in r:
            s += c.sum() / 3.0
    return s / (len(img) * len(img[0]))


def read_box(i, x, y, width, height, source_img, xy_factors, upper_left_corner, label="box"):
    x = int(x * xy_factors[0] + upper_left_corner[0])
    y = int(y * xy_factors[1] + upper_left_corner[1])
    width = int(width * xy_factors[0])
    height = int(height * xy_factors[1])
    s = 0
    img2 = i[y:y + height, x:x + width]
    for r in img2:
        for c in r:
            s += c.sum() / 3.0

    if DEBUG_SAVE_IMAGES:
        cv2.imwrite("./scans/boxes/" + label + ".png", img2)

    if (s / (width * height)) < SENSITIVITY or DEBUG_SHOW_ALL_BOXES:
        cv2.rectangle(source_img, (x, y), (x + width, y + height), (0, 255, 0), thickness=3)
    else:
        cv2.rectangle(source_img, (x, y), (x + width, y + height), (200, 200, 200), thickness=3)

    return (s / (width * height)) < SENSITIVITY


def get_corners(img):
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    target_colour = np.uint8([[[0, 0, 235]]])
    target_hsv = cv2.cvtColor(target_colour, cv2.COLOR_BGR2HSV)[0][0]
    lower_red = np.array([0 if target_hsv[0] < 10 else target_hsv[0] - 10, 150, 150])
    upper_red = np.array([255 if target_hsv[0] > 244 else target_hsv[0] + 10, 255, 255])
    mask = cv2.inRange(img_hsv, lower_red, upper_red)
    res = cv2.bitwise_and(img, img, mask=mask)

    edged = cv2.Canny(res, 100, 200)
    edged = cv2.blur(edged, (5, 5))

    (cnts, _, _) = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]

    boxes = []

    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            boxes += [approx]

    x_coords = []
    y_coords = []
    for box in boxes:
        for point in box:
            x_coords.append(point[0][0])
            y_coords.append(point[0][1])
            # cv2.drawContours(img, [box], -1, (0, 255, 0), 3)

    upper_left_corner = (min(x_coords), min(y_coords))
    lower_right_corner = (int(max(x_coords)), max(y_coords))

    return upper_left_corner, lower_right_corner


def scan_sheet(filename):
    source = cv2.imread(filename)
    img = source[:]

    upper_left_corner, lower_right_corner = get_corners(img)

    target_angle = math.degrees(math.tan(SHEET_HEIGHT / SHEET_WIDTH))
    current_angle = math.degrees(math.tan(
            float(int(lower_right_corner[1] / 10) - int(upper_left_corner[1]) / 10) / float(
                    int(lower_right_corner[0] / 10) - int(upper_left_corner[0] / 10))))

    angle_diff = current_angle - target_angle

    rows, cols, depth = img.shape
    M = cv2.getRotationMatrix2D(upper_left_corner, math.radians(angle_diff), 1)
    img = cv2.warpAffine(img, M, (cols, rows))
    # print "Rotated Image by " + str(math.fabs(angle_diff)) + " degrees."

    source = img[:]
    upper_left_corner, lower_right_corner = get_corners(img)
    cv2.rectangle(source, upper_left_corner, lower_right_corner, (255, 0, 0), thickness=10)

    if DEBUG_SHOW_AFTER_CORNERS:
        cv2.imshow("Image", cv2.resize(source, (int(850 * 0.7), int(1100 * 0.7))))
        cv2.waitKey(0)

    xy_factor = (
        (lower_right_corner[0] - upper_left_corner[0]) / SHEET_WIDTH, (lower_right_corner[1] - upper_left_corner[1]) / SHEET_HEIGHT)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    flag, img = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    data = {}
    fields, field_headers = load_field_data()

    for field in fields:
        field_type = field[0]
        if field_type == "Markers":
            marker_size = float(field[1])
        if field_type == "Digits":
            x = float(field[2])
            y = float(field[3])
            nums = ""
            for i in range(4):
                parts = [read_box(img, x + float(field[5]) + float(field[6]) * i, y, float(field[4]), float(field[5]),
                                  source, xy_factor, upper_left_corner, field[1] + str(i) + "0"),
                         read_box(img, x + float(field[6]) * i, y + float(field[5]), float(field[5]), float(field[4]),
                                  source, xy_factor, upper_left_corner, field[1] + str(i) + "1"),
                         read_box(img, x + float(field[6]) * i + float(field[5]) + float(field[4]), y + float(field[5]),
                                  float(field[5]), float(field[4]), source, xy_factor, upper_left_corner,
                                  field[1] + str(i) + "2"),
                         read_box(img, x + float(field[5]) + float(field[6]) * i, y + float(field[4]) + float(field[5]),
                                  float(field[4]), float(field[5]), source, xy_factor, upper_left_corner,
                                  field[1] + str(i) + "3"),
                         read_box(img, x + float(field[6]) * i, y + float(field[4]) + float(field[5]) + float(field[5]),
                                  float(field[5]), float(field[4]), source, xy_factor, upper_left_corner,
                                  field[1] + str(i) + "4"),
                         read_box(img, x + float(field[6]) * i + float(field[5]) + float(field[4]),
                                  y + float(field[4]) + float(field[5]) + float(field[5]), float(field[5]),
                                  float(field[4]), source, xy_factor, upper_left_corner, field[1] + str(i) + "5"),
                         read_box(img, x + float(field[5]) + float(field[6]) * i,
                                  y + (float(field[4]) + float(field[5])) * 2, float(field[4]), float(field[5]),
                                  source, xy_factor, upper_left_corner, field[1] + str(i) + "6")]
                for j in range(10):
                    if NUMBERS_MODEL[j] == parts:
                        nums += str(j)
                        break
                    if ALT_NUMBERS_MODEL[j] == parts:
                        nums += str(j)
                        break
                else:
                    nums += "_"
            data[field[1]] = nums
        if field_type == "Barcode":
            name = field[1]
            digits = len(bin(int("9" * int(field[2])))[2:])
            x_coord = float(field[3])
            y_coord = float(field[4])
            box_width = float(field[5])
            number = ""
            for i in range(digits):
                box_val = read_box(img, x_coord - ((i) * box_width), y_coord + 0.05, box_width, box_width, source,
                                   xy_factor, upper_left_corner, name + str(i))
                number = ("1" if box_val else "0") + number
            try:
                data[name] = str(int(number, 2))
            except:
                data[name] = "____"

            print(data[name])

        if field_type == "BoxNumber":
            name = field[1]
            digits = int(field[2])
            x_coord = float(field[3])
            y_coord = float(field[4])
            box_width = float(field[5])
            box_spacing = float(field[6])
            y_spacing = float(field[7])
            number = ""
            for i in range(digits):
                values = []
                for j in range(10):
                    box_val = read_box(img, x_coord + j * (box_width + box_spacing), y_coord + (y_spacing * 1.5 * i),
                                       box_width, box_width, source, xy_factor, upper_left_corner,
                                       name + str(i) + str(j))
                    values.append(box_val)
                if True in values:
                    number += str(max([a * b for a, b in zip(values, range(0, 10))]))
                else:
                    number += "_"
            data[field[1]] = number
        if field_type == "HorizontalOptions":
            name = field[1]
            x_coord = float(field[2])
            y_coord = float(field[3])
            box_width = float(field[4])
            box_spacing = float(field[5])
            options = field[6].split(" ")
            data_type = ""
            for op in options:
                if len(options) == 1:
                    data_type = "Boolean"
                    break
                try:
                    if not str(int(op.strip("+"))) == op.strip("+"):
                        data_type = "String"
                        break
                except:
                    data_type = "String"
                    break
            else:
                data_type = "Numbers"

            values = []
            for i in range(len(options)):
                label = options[i]
                box_val = read_box(img, x_coord + i * (box_width + box_spacing), y_coord, box_width, box_width, source,
                                   xy_factor, upper_left_corner, name + str(i))
                values.append(box_val)

            # print values
            if data_type == "String":
                for i in range(len(values)):
                    if values[i]:
                        data[name] = options[i]
            elif data_type == "Numbers":
                total = 0
                for i in range(len(values)):
                    if values == [False, False, False, False, False, False, False]:
                        data[name] = 0
                        break
                    elif values == [False, True, False, False, True, False, False]:
                        data[name] = 1
                        break
                    elif values[i]:
                        if options[i] in "+":
                            total += int(options[i].strip("+"))
                        else:
                            total = int(options[i].strip("+"))
                data[name] = total
            elif data_type == "Boolean":
                data[name] = values[0] * 1
        if field_type == "BulkOptions":
            name = field[1]
            headers = field[2].split(" ")
            x_coord = float(field[3])
            y_coord = float(field[4])
            box_size = float(field[5])
            box_spacing = float(field[6])
            options = field[7].split(" ")
            bulk_data = {}
            for i in range(len(headers)):
                header = headers[i]
                bool_values = []
                values = []
                for j in range(len(options)):
                    bool_values.append(
                            read_box(img, x_coord + i * (box_size + box_spacing),
                                     y_coord + j * (box_size + box_spacing),
                                     box_size, box_size, source, xy_factor, upper_left_corner, name + str(i) + str(j)))
                for k in range(len(bool_values)):
                    if bool_values[k]:
                        values.append(options[k])
                bulk_data[header] = values
            data[name] = bulk_data
        if field_type == "Image":
            name = field[1]
            x_coord = float(field[2])
            y_coord = float(field[3])
            width = float(field[4])
            height = float(field[5])
            x_coords = (int(x_coord * xy_factor[0] + upper_left_corner[0]),
                        int((x_coord + width) * xy_factor[0] + upper_left_corner[0]))
            y_coords = (int(y_coord * xy_factor[1] + upper_left_corner[1]),
                        int((y_coord + height) * xy_factor[1] + upper_left_corner[1]))
            crop = img[y_coords[0]:y_coords[1], x_coords[0]:x_coords[1]]
            img_value = avg_value(crop)
            if img_value > 1:
                cv2.imwrite("./scans/images/" + str(data["Team Number"]) + "-" + str(
                        data["-EncodedMatchData"]) + "_" + name + ".png", crop)
            data[name] = img_value
            cv2.rectangle(source, (x_coords[0], y_coords[0]), (x_coords[1], y_coords[1]),
                          ((200, 200, 200) if img_value > 1 else (0, 255, 0)), thickness=3)

    data["Match"] = data["-EncodedMatchData"][0:-1]
    data["Pos"] = data["-EncodedMatchData"][-1]

    del data["-EncodedMatchData"]

    field_headers = ["Match", "Pos", "Team Number"] + field_headers

    return data, source, field_headers


def web_scan(filename):
    data, img, headers = scan_sheet(filename)
    img_filename = "./static/temp_sheet.jpg"
    if path.isfile(img_filename):
        remove(img_filename)
    cv2.imwrite(img_filename, img)
    return img_filename, data, filename
