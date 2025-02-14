from flask import Flask,render_template,Response,jsonify
from keras.models import load_model
import cv2
import numpy as np
import mediapipe as mp
from imutils.video import VideoStream
mp_holistic = mp.solutions.holistic # Holistic model
mp_drawing = mp.solutions.drawing_utils # Drawing utilities
app=Flask(__name__)
model = load_model('sign_language_prediction.h5')
def mediapipe_detection(image, model):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # COLOR CONVERSION BGR 2 RGB
    image.flags.writeable = False                  # Image is no longer writeable
    results = model.process(image)                 # Make prediction
    image.flags.writeable = True                   # Image is now writeable 
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) # COLOR COVERSION RGB 2 BGR
    return image, results

def draw_landmarks(image, results):
    mp_drawing.draw_landmarks(image, results.face_landmarks, mp_holistic.FACEMESH_TESSELATION) # Draw face connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS) # Draw pose connections
    mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS) # Draw left hand connections
    mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS) # Draw right hand con


def draw_styled_landmarks(image, results):
    # Draw face connections
    mp_drawing.draw_landmarks(image, results.face_landmarks, mp_holistic.FACEMESH_TESSELATION, 
                             mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1), 
                             mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
                             ) 
    # Draw pose connections
    mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS,
                             mp_drawing.DrawingSpec(color=(80,22,10), thickness=2, circle_radius=1), 
                             mp_drawing.DrawingSpec(color=(80,44,121), thickness=2, circle_radius=1)
                             ) 
    # Draw left hand connections
    mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS, 
                             mp_drawing.DrawingSpec(color=(121,22,76), thickness=2, circle_radius=1), 
                             mp_drawing.DrawingSpec(color=(121,44,250), thickness=2, circle_radius=1)
                             ) 
    # Draw right hand connections  
    mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS, 
                             mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=1), 
                             mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=1)
                             )
    

def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])

actions=['afternoon', 'asl', 'baby', 'bad', 'bathroom', 'blue', 'book',
       'boy', 'brother', 'bye', 'chat', 'cheese', 'children', 'class',
       'cook', 'cookies', 'day', 'deaf', 'dog', "don't want", 'drink',
       'eat-food', 'father', 'fine', 'finish', 'forget', 'girl', 'go',
       'good', 'grandfather', 'grandmother', 'hamburger', 'happy',
       'hello', 'help', 'home', 'hour', 'husband', 'kitchen', 'know',
       'like', 'living room', 'look, see, watch', 'man', 'milk', 'minute',
       'month', 'more', 'mother', 'need', 'night', 'no', 'noon', 'not',
       'not yet', 'orange', 'pay attention', 'pink', 'please', 'right',
       'sad', 'sentence', 'signing', 'so-so', 'student', 'thank-you',
       'time', 'want', 'week', 'when', 'where', 'who', 'wife', 'woman',
       'wrong', 'year', 'yes', 'you', 'your']

from scipy import stats
colors = [(245,117,16), (117,245,16), (16,117,245)]
def prob_viz(res, actions, input_frame, colors):
    output_frame = input_frame.copy()
    for num, prob in enumerate(res):
        color_index = num % len(colors)  # Get index within color list length
    return output_frame
predicted_actions=None
def display_video():
    sequence = []
    sentence = []
    predictions = []
    threshold = 0.5
    cap = VideoStream(src=0).start()
    # Set mediapipe model 
    with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        while True:
            # Read feed
            frame = cap.read()

            # Make detections
            image, results = mediapipe_detection(frame, holistic)
            
            # Draw landmarks
            draw_styled_landmarks(image, results)
            
            # 2. Prediction logic
            keypoints = extract_keypoints(results)
            sequence.append(keypoints)
            sequence = sequence[-7:]
            
            if len(sequence) == 7:
                res = model.predict(np.expand_dims(sequence, axis=0))[0]
                predicted_actions=actions[np.argmax(res)]
                print(actions[np.argmax(res)])
                predictions.append(np.argmax(res))
                
                
                #3. Viz logic
                if np.unique(predictions[-7:])[0]==np.argmax(res): 
                    if res[np.argmax(res)] > threshold: 
                        
                        if len(sentence) > 0: 
                            if actions[np.argmax(res)] != sentence[-1]:
                                sentence.append(actions[np.argmax(res)])
                        else:
                            sentence.append(actions[np.argmax(res)])

                if len(sentence) > 5: 
                    sentence = sentence[-5:]

                # Viz probabilities
                image = prob_viz(res, actions, image, colors)
                
            cv2.rectangle(image, (0,0), (640, 40), (245, 117, 16), -1)
            cv2.putText(image, ' '.join(sentence), (3,30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Show to screen
            encoded_frame = cv2.imencode('.jpg', image)[1].tobytes()
            yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')

            if cv2.waitKey(10) & 0xFF == ord('q'):
               break
        cap.release()
        cv2.destroyAllWindows()

@app.route('/')
def index():
    return render_template('index2nd.html')

@app.route('/stop_loop')
def stop_loop():
    return render_template('index2nd.html')

@app.route('/video')
def video():
    return render_template('result.html')

@app.route('/capture')
def capture():
    return Response(display_video(),mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_prediction')
def get_prediction():
    return jsonify({'predicted_action': predicted_actions})

if __name__=="__main__":
    app.run(debug=True)
