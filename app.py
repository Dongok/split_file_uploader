import os.path

from flask import Flask, request, make_response, Response
from pprint import pprint
import glob
import pathlib
import functools
import json

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route("/upload", methods=["POST"])
def save_file():
    for a in request.form.items():
        print(a)

    for b in request.files.items():
        print(b)

    if 'chunk' not in request.files:
        return Response("file not exits", status=400)

    req_file = request.files['chunk']
    pprint(req_file)

    chunkNumber = request.form.get('chunkNumber', type=int)
    totalChunk = request.form.get('totalChunks', type=int)

    print("chunkNUmber={0}, totalChunk={1}".format(chunkNumber, totalChunk))

    pprint(request.files)

    target_path = pathlib.Path('./tmp').resolve()
    complete_target_path = pathlib.Path('./tmp_complte').resolve()
    
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    if not complete_target_path.exists():
        os.makedirs(complete_target_path)

    save_file_path = target_path.joinpath(str(chunkNumber))
    
    next_chunk = 0
    if save_file_path.exists():
        exist_file_size = os.stat(save_file_path).st_size
        req_file_length = int(request.headers.get("Content-Length"))
        print(exist_file_size,req_file_length)
        if exist_file_size != req_file_length:
            req_file.save(save_file_path)
            req_file.close()    
        else:
            chunk_file_list = glob.glob(str(target_path.joinpath("*")))
            next_chunk = int(os.path.basename(sorted(chunk_file_list,key=functools.cmp_to_key(conv_num),reverse=True)[1]))
    else:
        req_file.save(save_file_path)
        req_file.close()

    if chunkNumber == (totalChunk - 1):
        complete_file_path = complete_target_path.joinpath("target.file")
        if os.path.exists(complete_file_path):
            os.remove(complete_file_path)

        with open(complete_file_path, mode='bw') as complete_file:
            chunk_file_list = glob.glob(str(target_path.joinpath("*")))
            #print(chunk_file_list)
            for chunk_file in sorted(chunk_file_list,key=functools.cmp_to_key(conv_num)):
                print(chunk_file)
                with open(chunk_file,'br') as tmp_chunk:
                    complete_file.write(tmp_chunk.read())
                    tmp_chunk.close()

            complete_file.close()

        return Response("file upload complete", status=200)

    if next_chunk > 0:
        return Response(json.dumps({"next_chunk":next_chunk}), status=206)
    else:
        return Response(json.dumps({'msg':'next'}) , status=206)

def conv_num(a,b):
    if int(os.path.basename(a)) > int(os.path.basename(b)):
        return 1
    return -1

@app.route('/upload_ui', methods=['GET'])
def return_upload_ui():
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    
      title = <input type=text name='title'>
      file = <input type=file id='file' name=file>
      <input type='button' value=Upload onclick='split_upload()'>
    
    
    <div id='result'></div>
    
    <script type='text/javascript'>
    function split_upload() {
        const chunkSize = 1024 * 1024 * 10 ; // 10MB
        const file = document.getElementById("file").files[0];
        console.log(file)
        const resultElement = document.getElementById("result");
        
        const totalChunks = Math.ceil(file.size / chunkSize);
        let currentChunk = 0;
        
        const sendNextChunk = () => {
  			
  			// chunk size 만큼 데이터 분할
            const start = currentChunk * chunkSize;
            const end = Math.min(start + chunkSize, file.size);

            const chunk = file.slice(start, end);
			
  			// form data 형식으로 전송
            const formData = new FormData();
            formData.append("chunk", chunk, file.name);
            formData.append("chunkNumber", currentChunk);
            formData.append("totalChunks", totalChunks);

            fetch("/upload", {
                method: "POST",
                body: formData,
                header: {'Content-Length':chunk.size}
            }).then(resp => {
  				// 전송 결과가 206이면 다음 파일 조각 전송
                if (resp.status === 206) {
  					// 진행률 표시
                    // 
                    resp.text().then(data => {
                        j_data = JSON.parse(data)
                        console.log(j_data);
                        if(j_data['next_chunk']){
                            currentChunk = j_data['next_chunk']
                        }
                    });
                    resultElement.textContent = Math.round(currentChunk / totalChunks * 100) + "%"
                    currentChunk++;
                    if (currentChunk < totalChunks) {
                        sendNextChunk();
                    }
                // 마지막 파일까지 전송 되면 
                } else if (resp.status === 200) {
                    resp.text().then(data => resultElement.textContent = data);
                }
            }).catch(err => {
                console.error(err);
                console.error("Error uploading video chunk");
            });
        };

        sendNextChunk();
    }
    </script>
    '''


if __name__ == '__main__':
    app.run()
