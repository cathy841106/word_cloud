#coding:utf-8
import io, traceback
from flask.views           import MethodView
from flask                 import jsonify, g, request, send_file
from settings.environment  import app, error_return
from controller.word_cloud.word_cloud import word_cloud_multiple, word_cloud, read_text

class WordCloud(MethodView):
    def post(self):
        api_result = {}
        try:
            required = set(['text'])
            missing = required - set(request.json.keys())
            if len(missing)>0 :
                return error_return('{} is required'.format(', '.join(missing)), 400)

            text = request.json.get('text')
            top_N = int(request.form.get('top_N', 10))

            word_cloud_result = word_cloud(text, top_N=top_N) 

            api_result['status'] = 'success'
            api_result['data'] = word_cloud_result
            return api_result
        except ValueError as e:
            return error_return(str(e), 400)
        except Exception as e:
            traceback.print_exc()
            return error_return(str(e), 500)

class WordCloudExcel(MethodView):
    def post(self):
        try:
            required = set(['file'])
            missing = required - set(request.files.keys())
            if len(missing)>0 :
                return error_return('{} is required'.format(', '.join(missing)), 400)

            file = request.files.get('file')
            top_N = int(request.form.get('top_N', 10))

            text_list = read_text(file.read()) 
            word_cloud_result = word_cloud_multiple(text_list, top_N=top_N) 

            result_string = ''
            for word, count in word_cloud_result:
                result_string += '{} {}\n'.format(word, str(count))
            
            string_io = io.StringIO()
            string_io.write(result_string)
            return_file = io.BytesIO()
            return_file.write(string_io.getvalue().encode())
            return_file.seek(0)

            return send_file(return_file,
                attachment_filename='word_cloud.txt',
                as_attachment=True
                )
        except ValueError as e:
            return error_return(str(e), 400)
        except Exception as e:
            traceback.print_exc()
            return error_return(str(e), 500)


word_cloud_excel_view = WordCloudExcel.as_view('word_cloud_excel')
word_cloud_view = WordCloud.as_view('word_cloud')