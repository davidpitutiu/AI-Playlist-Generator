import os
from groq import Groq

client = Groq(api_key="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")

file_path = 'liked_songs_detailed.txt'

with open(file_path, 'r') as file:
    liked_songs = file.read().strip().splitlines()

def send_song_batch(songs, prompt):
    songs_text = "\n".join(songs)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI that will receive a list with a user's liked songs and a prompt based on these; you will return a list of songs."
            },
            {
                "role": "user",
                "content": songs_text
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

prompt = "Give me a list of songs with Romanian singers"

batch_size = 10

responses = []

total_batches = len(liked_songs) // batch_size + (1 if len(liked_songs) % batch_size > 0 else 0)

for i in range(0, len(liked_songs), batch_size):
    batch = liked_songs[i:i + batch_size]
    response = send_song_batch(batch, prompt)
    responses.append(response)

    current_batch = i // batch_size + 1
    print(f"Processed batch {current_batch} of {total_batches}")

output_file_path = 'generated_playlist.txt'

with open(output_file_path, 'w') as output_file:
    for res in responses:
        output_file.write(res + "\n")

print(f"Playlist generated and saved to {output_file_path}")
