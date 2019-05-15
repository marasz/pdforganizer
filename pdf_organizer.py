# This Python file uses the following encoding: utf-8
import PyPDF2
import os

import nltk
from nltk import word_tokenize
from nltk import FreqDist
import yaml
from pathlib import Path
import datetime
import textract

with open("config.yaml", 'r') as stream:
    try:
        config = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)

source_folder = Path(config['source_folder'])
target_folder = Path(config['target_folder'])
default_folder = Path(config['default_folder'])
original_move_folder = Path(config['original_move_folder'])
folder_keywords = config['folders']
split_pdf = config['split_pdf']
print_paths = config['print_paths']


#analyzer = TfidfVectorizer().build_analyzer()

umlauts = {
    ord('Ä'):'Ae',
    ord('ä'):'ae',
    ord('Ö'):'Oe',
    ord('ö'):'oe',
    ord('Ü'):'Ue',
    ord('ü'):'ue'
    }


def import_stopwords(path):
    stopwords_d = []
    with open(path, 'r', encoding='utf_8') as file:
        for line in file:
            stopwords_d.append(line.replace('\n','').lower().translate(umlauts))
    return stopwords_d


stopwords_d = import_stopwords("GermanST_utf8.txt")


def translate_umlauts(doc):
    return (w.translate(umlauts) for w in doc)


def split_pdfs(directory):
    for file in os.listdir(directory):
        if str(file).endswith('.pdf'):
            split_pdf(str(os.path.join(directory,file)))


def split_pdf(path):
    pdf_file = open(path,'rb')
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)
    pageNumbers = pdf_reader.getNumPages()
    now = datetime.datetime.now()

    for i in range (pageNumbers):
        pdf_writer = PyPDF2.PdfFileWriter()
        pdf_writer.addPage(pdf_reader.getPage(i))
        file_name = now.strftime("%Y-%m-%d") + "_" + str(now.microsecond) + "_" + 'Scan_' + str(i+1) + '.pdf'
        file = open(str(os.path.join(source_folder, file_name)), 'wb')
        pdf_writer.write(file)
        file.close()
    pdf_file.close()

    if not os.path.exists(str(os.path.join(original_move_folder))):
        os.makedirs(str(os.path.join(original_move_folder)))
    os.rename(path, str(os.path.join(original_move_folder, now.strftime("%Y-%m-%d") + "_" + str(now.microsecond) +'_Scan.pdf')))


def convert_pdf_to_txt(path):
    text = textract.process(path)
    text = text.decode('UTF-8', errors='ignore')
    return text


def tokenize_pdf(path):
    text = []
    text = convert_pdf_to_txt(path)
    tokens = [word for word in word_tokenize(text) if word not in stopwords_d and len(word) > 2]
    return tokens


def tokenize_pdfs(directory):
    tags = []
    tokens = []
    for subdir, dirs, files in os.walk(directory):
        for file in files:
            if str(file).endswith('.pdf'):
                if split_pdf:
                    split_pdf(str(os.path.join(subdir, file)))
                tags.append(subdir.replace(directory, '').split(os.sep))
                tokens.append(tokenize_pdf(str(os.path.join(subdir, file))))

    return tags, tokens


def categorize_pdfs(directory):
    for file in os.listdir(directory):
        if str(file).endswith('.pdf'):
            tokens = tokenize_pdf(os.path.join(directory, str(file)))
            fdist = FreqDist(word.lower() for word in tokens)
            ranking = {}
            keywords = {}
            for folder in folder_keywords:
                ranking[folder] = sum([fdist[keyword] for keyword in folder_keywords[folder]])
                keywords[folder] = [(keyword, fdist[keyword]) for keyword in folder_keywords[folder]]
            sorted_ranking = sorted(ranking.items(), key=lambda kv: kv[1], reverse=True)
            if sorted_ranking[0][1] == 0:
                if not os.path.exists(default_folder):
                    os.makedirs(default_folder)
                os.rename(str(os.path.join(directory, file)), str(os.path.join(default_folder, file)))
                if print_paths:
                    print(str(os.path.join(default_folder, file)))
            else:
                keyword = sorted(keywords[sorted_ranking[0][0]],key=lambda kv: kv[1], reverse=True)[0][0]
                if not os.path.exists(str(os.path.join(target_folder, sorted_ranking[0][0]))):
                    os.makedirs(str(os.path.join(target_folder, sorted_ranking[0][0])))
                filename = create_filename(folder, keyword)
                os.rename(str(os.path.join(directory, file)), str(os.path.join(target_folder, sorted_ranking[0][0],filename)))
                if print_paths:
                    print(str(os.path.join(target_folder, sorted_ranking[0][0],filename)))


def create_filename(folder, key):
        now = datetime.datetime.now()
        filename = config['save_pattern']
        filename = filename.replace('%d', now.strftime(config['date_format']))
        filename = filename.replace('%k', key)
        filename = filename.replace('%f', folder)
        filename = filename.replace('%m', str(now.microsecond))
        filename = filename + ".pdf"
        return filename


if split_pdf:
    split_pdfs(source_folder)

categorize_pdfs(source_folder)
