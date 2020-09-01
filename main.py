import os
import json
import shutil
import xml.etree.cElementTree as ET
from tqdm import tqdm
from PIL import Image

DIRECTORY_WITH_IMAGES = 'images/'
DIRECTORY_WITH_ANNOTATIONS = 'markup/'
DATABASE_NAME = 'ORI_Markup'
IMAGE_DEPTH_DEFAULT = 3


def main():
    with open('config.json') as config_str:
        config = json.load(config_str)
        input_format = config.get('input_format')
        output_format = config.get('output_format')
        input_path = config.get('input_path')
        output_path = config.get('output_path')

        if validate(input_format, output_format, input_path, output_path):
            data_set = read_data_set(input_path, input_format)
            write_data_set(data_set, output_path, output_format)
            copy_images(input_path, output_path)


def validate(input_format, output_format, input_path, output_path):
    format_types = ['internal', 'internalCSV', 'pascalVOC']
    is_validate = True

    if input_path == output_path:
        is_validate = False
        print('ERROR: Входной и выходной пути до датасетов должны быть различными')

    if format_types.count(input_format) == 0 or format_types.count(output_format) == 0:
        is_validate = False
        print('ERROR: Неверно задан формат датасет, допустимые значения: ' + '|'.join(format_types))

    if not os.path.isdir(input_path):
        is_validate = False
        print('ERROR: Неверно задана директория с исходным датасетом: ' + input_path)

    if not os.path.isdir(output_path):
        try:
            os.makedirs(output_path)
        except OSError:
            is_validate = False
            print('ERROR: Не удается создать директорию: ' + output_path)

    return is_validate


def read_data_set(path_to_data_set, format_data_set):
    data_set = []

    if format_data_set == 'internal':
        annotations_directory_path = path_to_data_set + '/' + DIRECTORY_WITH_ANNOTATIONS
        images_directory_path = path_to_data_set + '/' + DIRECTORY_WITH_IMAGES
        list_filenames = os.listdir(annotations_directory_path)
        progress_bar = tqdm(desc='Начитываем исходный датасет', total=len(list_filenames))

        for filename in list_filenames:
            try:
                with open(annotations_directory_path + filename) as file:
                    width = height = 0
                    annotations = json.loads(file.read())
                    image_path = images_directory_path + filename.rsplit('.', 1)[0] + '.jpg'

                    try:
                        with Image.open(image_path) as img:
                            width, height = img.size
                    except:
                        print('ERROR: Ошибка чтения файла: ' + image_path)

                    for rowData in annotations:
                        data_set.append({
                            'filename': filename.rsplit('.', 1)[0],
                            'width': str(width),
                            'height': str(height),
                            'label': rowData.get('label'),
                            'x_min': str(rowData.get('x')),
                            'y_min': str(rowData.get('y')),
                            'x_max': str(rowData.get('x1')),
                            'y_max': str(rowData.get('y1'))
                        })

                    progress_bar.update()

            except:
                print('ERROR: Ошибка чтения файла: ' + annotations_directory_path + filename)

    elif format_data_set == 'internalCSV':
        with open(path_to_data_set + '/markup.csv') as file:
            # Считаем первую строку с названиями полей
            file.readline().split(',')
            rows = file.read().splitlines()
            progress_bar = tqdm(desc='Начитываем исходный датасет', total=len(rows))

            for row in rows:
                row_data = row.split(',')
                relative_path_to_image = row_data[0]
                filename_with_extension = relative_path_to_image.rsplit('/', 1)[-1]
                filename = filename_with_extension.rsplit('.', 1)[0]
                data_set.append({
                    'filename': filename,
                    'width': row_data[1],
                    'height': row_data[2],
                    'label': row_data[3],
                    'x_min': row_data[4],
                    'y_min': row_data[5],
                    'x_max': row_data[6],
                    'y_max': row_data[7]
                })
                progress_bar.update()

    elif format_data_set == 'pascalVOC':
        try:
            tree = ET.ElementTree(file=path_to_data_set + '/markup.xml')
        except FileNotFoundError:
            print('ERROR: Отсутствует необходимый файл: ' + path_to_data_set + '/markup.xml')
            return data_set

        root = tree.getroot()
        progress_bar = tqdm(desc='Начитываем исходный датасет', total=len(root))

        for annotation in root:
            annotation_objects = annotation.findall('object')
            size_image = annotation.find('size')

            for object_info in annotation_objects:
                bnd_box = object_info.find('bndbox')
                data_set.append({
                    'filename': annotation.find('filename').text.rsplit('.', 1)[0],
                    'width': size_image.find('width').text,
                    'height': size_image.find('height').text,
                    'label': object_info.find('name').text,
                    'x_min': bnd_box.find('xmin').text,
                    'y_min': bnd_box.find('ymin').text,
                    'x_max': bnd_box.find('xmax').text,
                    'y_max': bnd_box.find('ymax').text
                })

            progress_bar.update()

    return data_set


def write_data_set(data_set, path_for_data_set, format_data_set):
    progress_bar = tqdm(desc='Конвертируем', total=len(data_set))

    if format_data_set == 'internal':
        index = 0
        labels = {}
        list_annotations = []
        annotations_directory_path = path_for_data_set + '/' + DIRECTORY_WITH_ANNOTATIONS

        if not os.path.isdir(annotations_directory_path):
            os.makedirs(annotations_directory_path)

        while index < len(data_set):
            row_data = data_set[index]
            filename = row_data.get('filename')
            labels[row_data.get('label')] = True
            list_annotations.append({
                'x': int(row_data.get('x_min')),
                'y': int(row_data.get('y_min')),
                'x1': int(row_data.get('x_max')),
                'y1': int(row_data.get('y_max')),
                'label': row_data.get('label')
            })
            progress_bar.update()

            if index + 1 == len(data_set) or filename != data_set[index + 1].get('filename'):
                with open(annotations_directory_path + filename + '.json', 'w') as file:
                    file.write(json.dumps(list_annotations))
                    list_annotations = []

            index += 1

        with open(path_for_data_set + '/' + 'meta.json', 'w') as file:
            file.write(json.dumps({'labels': list(labels.keys())}))

    elif format_data_set == 'internalCSV':
        output_data = 'filename,width,height,class,xmin,ymin,xmax,ymax'

        for row_data in data_set:
            relative_image_path = DIRECTORY_WITH_IMAGES + row_data.get('filename') + '.jpg'
            output_data += '\n'
            output_data += ','.join([
                relative_image_path, str(row_data.get('width')), str(row_data.get('height')),
                str(row_data.get('label')), str(row_data.get('x_min')), str(row_data.get('y_min')),
                str(row_data.get('x_max')), str(row_data.get('y_max'))
            ])
            progress_bar.update()

        with open(path_for_data_set + '/markup.csv', 'w') as file:
            file.write(output_data)

    elif format_data_set == 'pascalVOC':
        root = ET.Element('annotations')
        previous_filename = ''

        for row_data in data_set:
            filename = row_data.get('filename') + '.jpg'
            path_to_image = path_for_data_set + '/' + DIRECTORY_WITH_IMAGES + filename

            if previous_filename != filename:
                previous_filename = filename
                annotation_xml = ET.SubElement(root, 'annotation')
                folder_xml = ET.SubElement(annotation_xml, 'folder')
                filename_xml = ET.SubElement(annotation_xml, 'filename')
                path_xml = ET.SubElement(annotation_xml, 'path')
                source_xml = ET.SubElement(annotation_xml, 'source')
                database_xml = ET.SubElement(source_xml, 'database')
                size_xml = ET.SubElement(annotation_xml, 'size')
                width_xml = ET.SubElement(size_xml, 'width')
                height_xml = ET.SubElement(size_xml, 'height')
                depth_xml = ET.SubElement(size_xml, 'depth')
                segmented_xml = ET.SubElement(annotation_xml, 'segmented')

                folder_xml.text = DIRECTORY_WITH_IMAGES[:-1]
                filename_xml.text = filename
                path_xml.text = path_to_image
                database_xml.text = DATABASE_NAME
                width_xml.text = row_data.get('width')
                height_xml.text = row_data.get('height')
                depth_xml.text = str(IMAGE_DEPTH_DEFAULT)
                segmented_xml.text = '0'

            object_xml = ET.SubElement(annotation_xml, 'object')
            object_name_xml = ET.SubElement(object_xml, 'name')
            object_pose_xml = ET.SubElement(object_xml, 'pose')
            object_truncated_xml = ET.SubElement(object_xml, 'truncated')
            object_difficult_xml = ET.SubElement(object_xml, 'difficult')
            object_bndbox_xml = ET.SubElement(object_xml, 'bndbox')
            bndbox_xmin_xml = ET.SubElement(object_bndbox_xml, 'xmin')
            bndbox_ymin_xml = ET.SubElement(object_bndbox_xml, 'ymin')
            bndbox_xmax_xml = ET.SubElement(object_bndbox_xml, 'xmax')
            bndbox_ymax_xml = ET.SubElement(object_bndbox_xml, 'ymax')

            object_name_xml.text = row_data.get('label')
            object_pose_xml.text = 'Unspecified'
            object_truncated_xml.text = '0'
            object_difficult_xml.text = '0'
            bndbox_xmin_xml.text = row_data.get('x_min')
            bndbox_ymin_xml.text = row_data.get('y_min')
            bndbox_xmax_xml.text = row_data.get('x_max')
            bndbox_ymax_xml.text = row_data.get('y_max')

            progress_bar.update()

        with open(path_for_data_set + '/markup.xml', 'w') as fh:
            fh.write(ET.tostring(root, 'utf-8').decode('utf-8'))


def copy_images(input_path, output_path):
    input_path += '/' + DIRECTORY_WITH_IMAGES
    output_path += '/' + DIRECTORY_WITH_IMAGES

    if os.path.isdir(output_path):
        shutil.rmtree(output_path)

    progress_bar = tqdm(desc='Копируем директорию images/', total=len(os.listdir(input_path)))
    shutil.copytree(input_path, output_path, False, None, lambda src, dst: _copy_image(src, dst, progress_bar))


def _copy_image(src, dst, progress_bar):
    shutil.copy2(src, dst)
    progress_bar.update()


if __name__ == '__main__':
    main()
