from settings.environment         import app
from application.word_cloud.view  import word_cloud_view, word_cloud_excel_view

def test():
	return ('api running')

app.add_url_rule('/health'           , view_func=test                 , methods=['GET'])
app.add_url_rule('/word_cloud/'      , view_func=word_cloud_view      , methods=['POST'])
app.add_url_rule('/word_cloud/excel/', view_func=word_cloud_excel_view, methods=['POST'])

if __name__ == '__main__':
    app.run()
