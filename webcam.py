
import customtkinter as ctk
from PIL import Image
import cv2
from customtkinter import CTkImage
from pyzbar.pyzbar import decode
import json
from datetime import datetime
import os
from twilio.rest import Client

cap = cv2.VideoCapture(0)

# Paths for JSON records
sis_path = 'records/sis_smg.json'
Jc1_path = 'records/jc1.json'
Jc2_path = 'records/jc2.json'
Sec4_path = 'records/sec4.json'

# Paths for text attendance summaries
Jc1_txt = 'txtFile/jc1.txt'
Jc2_txt = 'txtFile/jc2.txt'
sec4_txt = "txtFile/sec4.txt"


# Ensure JSON file is cleared on program start
def clear_json(path):
    with open(path, 'w') as f:
        json.dump({}, f)


# Clear JSON attendance record on start
clear_json(sis_path)
clear_json(Jc1_path)
clear_json(Jc2_path)

# Initialize customtkinter settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Time limit for attendance
eight_am = datetime.strptime("08:00 AM", "%I:%M %p")


# Ensure JSON files exist
def ensure_json_exists(path):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump({}, f)


# Load JSON data
def load_json(path):
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# Save JSON data
def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


# Write a detailed attendance message to a text file
def write_attendance_message_with_content(grade, attendance_data, file_path):
    with open(file_path, 'w') as f:
        # Write the header message
        f.write(f"Hello Teacher of {grade},\n\n")

        # Write absent list
        f.write("Absent:\n")
        absent_students = [entry for entry in attendance_data.values() if entry['state'] == 'absent']
        if absent_students:
            for student in absent_students:
                f.write(f"- {student['name']} (Checked in at: {student['time']}, Date: {student['date']})\n")
        else:
            f.write("No absent students.\n")

        # Write a separator
        f.write("\n")

        # Write present list
        f.write("Present:\n")
        present_students = [entry for entry in attendance_data.values() if entry['state'] == 'present']
        if present_students:
            for student in present_students:
                f.write(f"- {student['name']} (Checked in at: {student['time']}, Date: {student['date']})\n")
        else:
            f.write("No present students.\n")

        # Confirmation message
        f.write("\nThis is the complete attendance summary for today.\n")


# Main customtkinter GUI setup
root = ctk.CTk()
root.title("Webcam Attendance System")
root.geometry("1000x600")  # Increase window size to allow more space for webcam feed

# Frame for webcam feed (increase width and height)
webcam_frame = ctk.CTkFrame(root)
webcam_frame.place(relwidth=0.75, relheight=0.9, relx=0.02, rely=0.05)  # Adjusted size for larger view
webcam_label = ctk.CTkLabel(webcam_frame, text="")
webcam_label.pack(fill="both", expand=True)  # Make label fill frame completely

# Frame for time display (move to a smaller space on the right)
time_frame = ctk.CTkFrame(root)
time_frame.place(relx=0.78, rely=0.05, relwidth=0.2, relheight=0.15)  # Adjust position and size
time_label = ctk.CTkLabel(time_frame, text="Time", font=("Helvetica", 16))
time_label.pack()

# Frame for list of earliest attendees
list_frame = ctk.CTkFrame(root)
list_frame.place(relx=0.78, rely=0.25, relwidth=0.2, relheight=0.7)  # Adjust position and size
list_label = ctk.CTkLabel(list_frame, text="Top 10 Earliest People", font=("Helvetica", 12))
list_label.pack()
people_listbox = ctk.CTkTextbox(list_frame, font=("Helvetica", 10), width=100, height=300)
people_listbox.pack(fill=ctk.BOTH, expand=True)


# Function to display webcam feed and handle QR scanning
def show_webcam():
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, 1)
        qr_info = decode(frame)

        if qr_info:
            qr = qr_info[0]
            data = qr.data.decode()
            rect = qr.rect
            cv2.putText(frame, data, (rect.left, rect.top), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 2)

            # Extract grade and name from QR code data
            student_name = data[4:]  # assuming last part is student name
            student_grade = data[:3]  # assuming first part is grade

            # Time check
            now = datetime.now()
            formatted_time = now.strftime("%I:%M %p")
            formatted_date = now.strftime("%Y-%m-%d")
            parsed_time = datetime.strptime(formatted_time, "%I:%M %p")
            state = 'absent' if parsed_time.time() > eight_am.time() else 'present'

            # Update attendance data
            student_data = load_json(sis_path)

            # Create a unique key for each student based on their grade and name
            entry_key = f"{student_grade}_{student_name}"

            student_data[entry_key] = {
                'name': student_name,
                'grade': student_grade,
                "time": formatted_time,
                'date': formatted_date,
                'state': state
            }

            # Save to the main attendance file
            save_json(sis_path, student_data)

            # Save to the specific grade path
            if student_grade == 'JC2':
                grade_data = load_json(Jc2_path)
                grade_data[entry_key] = student_data[entry_key]
                save_json(Jc2_path, grade_data)
            elif student_grade == 'JC1':
                grade_data = load_json(Jc1_path)
                grade_data[entry_key] = student_data[entry_key]
                save_json(Jc1_path, grade_data)
            elif student_grade == 'SC4':
                grade_data = load_json(Sec4_path)
                grade_data[entry_key] = student_data[entry_key]
                save_json(Sec4_path, grade_data)

            # Update displayed list with new entry
            people_listbox.delete("1.0", ctk.END)
            for key, value in student_data.items():
                people_listbox.insert(ctk.END, f"{value['name']} ({value.get('grade', 'N/A')}) -- {value['time']}\n")

        # Convert frame to RGB for Tkinter
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = CTkImage(light_image=img, dark_image=img,
                         size=(webcam_label.winfo_width(), webcam_label.winfo_height()))
        webcam_label.imgtk = imgtk
        webcam_label.configure(image=imgtk)

    webcam_label.after(10, show_webcam)


show_webcam()


# Function to update the time label
def update_time():
    current_time = datetime.now().strftime('%H:%M:%S')
    time_label.configure(text=current_time)
    root.after(1000, update_time)


update_time()

# Twilio credentials
account_sid = 'AC310c16b1a8835ef1218e6545bb2265d4'  # Replace with your Account SID
auth_token = '7a6a02329008af9c9b3ca39797b2c19e'  # Replace with your Auth Token
from_whatsapp_number = 'whatsapp:+14155238886'  # Twilio sandbox WhatsApp number

original = 'whatsapp:+628995393030'  # Teacher's WhatsApp number

to_whatsapp_number_Jc2 = 'whatsapp:+639274569484'  # Sammy
to_whatsapp_number_Jc1 = 'whatsapp:+6288988002956'  # Ben
to_whatsapp_number_Sec4 = 'whatsapp:+919884325621'  # Anuja
# Send attendance summary
def send_attendance_summary(grade, attendance_data):
    client = Client(account_sid, auth_token)

    # Format the attendance summary
    summary = f"Attendance Summary for {grade}:\n"
    for entry in attendance_data.values():
        summary += f"{entry['name']}: {entry['state']} at {entry['time']}\n"

    # Include a message about detailed text file
    summary += "\nDetailed attendance records have been saved locally."

    # Determine the recipient based on the grade
    if grade == 'JC1':
        recipient = to_whatsapp_number_Jc1
    elif grade == 'JC2':
        recipient = to_whatsapp_number_Jc2
    elif grade == 'SC4':
        recipient = to_whatsapp_number_Sec4
    else:
        print(f"Grade {grade} not recognized. No message sent.")
        return

    # Send the message
    message = client.messages.create(
        body=summary,
        from_=from_whatsapp_number,
        to=recipient
    )

    print(f"Message sent to {recipient}: {message.sid}")



# Handle window closing event
def on_closing():
    cap.release()

    # Load attendance data for each grade
    jc1_data = load_json(Jc1_path)
    jc2_data = load_json(Jc2_path)
    sec4_data = load_json(Sec4_path)

    # Write attendance summaries to text files
    if jc1_data:
        write_attendance_message_with_content("JC1", jc1_data, Jc1_txt)
        send_attendance_summary("JC1", jc1_data)
    if jc2_data:
        write_attendance_message_with_content("JC2", jc2_data, Jc2_txt)
        send_attendance_summary("JC2", jc2_data)
    if sec4_data:
        write_attendance_message_with_content("SEC4", sec4_data, sec4_txt)
        send_attendance_summary("SC4", sec4_data)

    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
