import os

def main():
    template_path = 'scheduler_api/templates/index.html'
    if not os.path.exists(template_path):
        print(f"Error: {template_path} does not exist!")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If the function is already there, let's skip to avoid duplicates
    if 'function changeRoomAllocation(' in content:
        print("changeRoomAllocation already exists in index.html!")
        return

    func_header = 'function filterTimeline(year) {'
    if func_header not in content:
        print("Error: filterTimeline function header not found!")
        return

    idx = content.find(func_header)
    brace_count = 0
    end_idx = -1
    for i in range(idx + len(func_header) - 1, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            if brace_count > 0:
                brace_count -= 1
            else:
                end_idx = i + 1
                break

    if end_idx == -1:
        print("Error: Could not find closing brace of filterTimeline!")
        return

    js_code = """

        function changeRoomAllocation(lectureId, currentRoom) {
            const newRoom = prompt("Enter new room designation / number for this slot:", currentRoom);
            if (newRoom === null) return;
            const trimmed = newRoom.trim();
            if (!trimmed) {
                alert("Room designation cannot be empty!");
                return;
            }
            
            fetch("/api/schedule/update-room/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    schedule_id: lectureId,
                    room_number: trimmed
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message || "Room updated successfully!");
                    location.reload();
                } else {
                    alert(data.error || "Failed to update room.");
                }
            })
            .catch(err => {
                console.error("Error updating room:", err);
                alert("An error occurred while updating the room designation.");
            });
        }"""

    new_content = content[:end_idx] + js_code + content[end_idx:]
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESSFULLY INSERTED changeRoomAllocation in index.html!")

if __name__ == '__main__':
    main()
