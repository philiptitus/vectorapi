import cv2
from deepface import DeepFace

def analyze_faces_and_emotions(video_path, frame_skip=5, resize_factor=0.5):
    """Detects faces and their emotions in a video."""
    cap = cv2.VideoCapture(video_path)
    
    # Initialize counters for emotion durations
    total_frames = 0
    calm_frames = 0
    emotion_counts = {}
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        # Resize frame
        frame = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces and analyze emotions
        results = DeepFace.analyze(rgb_frame, actions=['emotion'], enforce_detection=False, detector_backend='mtcnn')

        for result in results:
            face = result['region']
            x, y, w, h = face['x'], face['y'], face['w'], face['h']
            dominant_emotion = result['dominant_emotion']
            emotion_scores = result['emotion']

            # Draw bounding box and emotions on frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, dominant_emotion, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)

            # Print emotions
            print(f"Face detected at [{x}, {y}, {w}, {h}] with dominant emotion: {dominant_emotion}")
            print(f"Emotion scores: {emotion_scores}")

            # Increment frame counters
            total_frames += 1
            if dominant_emotion in ['neutral', 'happy']:
                calm_frames += 1

            # Update emotion count
            emotion_counts.setdefault(dominant_emotion, 0)
            emotion_counts[dominant_emotion] += 1

        # Display the frame
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Calculate and print calm percentage
    if total_frames > 0:
        calm_percentage = (calm_frames / total_frames) * 100
        print(f"Calm Percentage: {calm_percentage:.2f}%")
    else:
        print("No frames analyzed.")

    # Determine the most dominant emotion on average
    if emotion_counts:
        most_dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        print(f"Average Most Dominant Emotion: {most_dominant_emotion}")
    else:
        print("No dominant emotions detected.")

if __name__ == "__main__":
    video_path = r"C:\Users\HP\Desktop\stuff\CODING\PYTHON\PROJECTS\django\jennie\video\2042531d903aaeb5e17a51688a942005.mp4"
    analyze_faces_and_emotions(video_path)
