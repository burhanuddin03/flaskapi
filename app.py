from flask import Flask,request,jsonify,url_for,send_file
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from flask import abort
from detect2 import detect
import cv2
import uuid


#init app
app=Flask(__name__)
BASEDIR=os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(os.getcwd(),'uploads')

#database initialization
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///'+os.path.join(BASEDIR,'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

#Init db
db=SQLAlchemy(app)
#Init ma
ma=Marshmallow(app)



class Image(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.Text,nullable=False)
    mimetype=db.Column(db.Text,nullable=False)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True) 
    user_uid=db.Column(db.String(264),unique=True)
    
    def __repr__(self):
        return '<User {}>'.format(self.user_uid)


class ClassificationHistory(db.Model):
    id=db.Column(db.Integer,primary_key=True) 
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'))
    total_cost=db.Column(db.Integer)
    user=db.relationship('User',backref='user_photos')
    image=db.relationship('Image',backref='image')


    def __repr__(self):
        return '<ClassificationHistory: {}>.'.format(self.image_id)


class ImageHistory(ma.Schema):
    class Meta:
        model=ClassificationHistory
        fields=('id','user_id','image_id','total_cost','image_url')    
    
    image_url=ma.Hyperlinks({
        "url":ma.URLFor('get_image',values=dict(image_id='<image_id>')),
    })

    
    
imagehistory_schema=ImageHistory()
imagehistorys_schema=ImageHistory(many=True)

def get_image_file_name(filename):
    all_obj=Image.query.order_by(Image.id.desc()).first()
    image_id=1
    if Image.query.count()!=0:
        image_id=int(all_obj.id)+1
    filename="{}.{}".format(image_id,'jpg')
    return filename

@app.route('/uploads/<image_id>',methods=['GET'])
def get_image(image_id):
    image=Image.query.get(image_id)
    return send_file(os.path.join('uploads',image.name),mimetype='image/jpg')


@app.route('/send',methods=['POST'])
def add_image():
    image_file=request.files['file']
    user_id=request.form['uid']
    im0,total_sum=detect(image_file)

    #cv2.imwrite('D:\\FranceProject\\Dataset_Model\\models\\yolov5\\runs\\detect\\img.png',im0)
    image_filename=get_image_file_name(image_file.filename)
    cv2.imwrite(os.path.join(app.config['UPLOAD_FOLDER'],image_filename),im0)
    
    user=db.session.query(User).filter_by(user_uid=user_id).scalar()
    if user is None:
        if len(user_id)!=0:
            user=User(user_uid=user_id)
            db.session.add(user)
        else:
            return jsonify({'error':'Invalid Request make sure user id is not empty'})
    
    if not image_file:
        return jsonify({'error':'Invalid request make sure image is included'})
    
    image=Image(name=secure_filename(image_filename),mimetype='image/jpg')
    db.session.add(image)

    image_history=ClassificationHistory(user=user,image=image,total_cost=total_sum)
    db.session.add(image_history)
    db.session.commit()


    return imagehistory_schema.jsonify(image_history)

@app.route('/view-history/<uid>',methods=['GET'])
def get_list(uid):
    user=db.session.query(User).filter_by(user_uid=uid).scalar()
    if user is None:
        return jsonify({'message':'History is empty'})
    else:
        all_history=imagehistorys_schema.dump(user.user_photos)
        return jsonify(all_history)

@app.route('/view-history/<uid>/individual/<imgid>',methods=['GET'])
def get_details(uid,imgid):
    user=db.session.query(User).filter_by(user_uid=uid).scalar()
    if user is None:
        return abort(400,'Bad Request')
    image=db.session.query(Image).filter_by(id=imgid).scalar()
    if image is None:
        return abort(400,'Bad Request')

    history_detail=ClassificationHistory.query.filter_by(user_id=user.id,image_id=image.id).first()
    return imagehistory_schema.jsonify(history_detail)

# @app.route('/get_actual_image_url/<image_id>',methods=['GET'])
# def get_image_url(image_id):
#     imgid=image_id
#     image=db.session.query(Image).filter_by(id=imgid).scalar()
#     if image is None:
#         return abort(400,'Bad Request')
#     url=request.host_url[:-1]+url_for('get_image',filename=image.name)  
#     return jsonify({'image_url':url})    



#run server
if __name__ == "__main__":
    app.run(debug=True)
