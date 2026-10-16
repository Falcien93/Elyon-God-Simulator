using System;
using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace Elyon
{
    /// <summary>
    /// Living speech through the xAI Responses API. The key is never written into the garden record.
    /// </summary>
    public class GrokSpeech : MonoBehaviour
    {
        public const string Endpoint = "https://api.x.ai/v1/responses";
        public const string DefaultModel = "grok-4.7";
        public const string KeyFileName = "elyon-xai-key.txt";

        public string model = DefaultModel;

        public static string MissingKeyLine =>
            "The garden cannot hear a living mind yet. Type an xAI key below and keep it on this computer. It is stored only as elyon-xai-key.txt in this app's data folder, and it is never written into the garden record.";

        public static string KeyPath => Path.Combine(Application.persistentDataPath, KeyFileName);

        public static string LoadKey()
        {
            try
            {
                if (File.Exists(KeyPath))
                {
                    return File.ReadAllText(KeyPath).Trim();
                }

                string beside = Path.Combine(Directory.GetParent(Application.dataPath).FullName, "xai-key.local.txt");
                if (File.Exists(beside)) return File.ReadAllText(beside).Trim();
            }
            catch (Exception error)
            {
                Debug.LogWarning("Could not read the xAI key file: " + error.Message);
            }
            return "";
        }

        public static void SaveKey(string value)
        {
            string trimmed = (value ?? "").Trim();
            if (trimmed.Length == 0)
            {
                if (File.Exists(KeyPath)) File.Delete(KeyPath);
                return;
            }
            File.WriteAllText(KeyPath, trimmed);
        }

        public void Ask(Person person, string playerLine)
        {
            string key = LoadKey();
            if (string.IsNullOrEmpty(key))
            {
                person.HearLocal(MissingKeyLine, false);
                return;
            }
            StartCoroutine(Send(person, key, playerLine));
        }

        IEnumerator Send(Person person, string key, string playerLine)
        {
            string payload = BuildPayload(person, playerLine);
            byte[] body = Encoding.UTF8.GetBytes(payload);
            using var request = new UnityWebRequest(Endpoint, UnityWebRequest.kHttpVerbPOST);
            request.uploadHandler = new UploadHandlerRaw(body);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Authorization", "Bearer " + key);
            request.SetRequestHeader("Content-Type", "application/json");
            request.timeout = 45;
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                person.HearLocal(Friendly(request.responseCode, request.error), false);
                yield break;
            }

            string raw = request.downloadHandler.text ?? "";
            string spoken = ExtractSpeech(raw);
            person.HearLocal(spoken, true);
            person.Remember(ExtractField(spoken, "remember"));
            person.ApplyTrust(ExtractTrust(spoken));
        }

        string BuildPayload(Person person, string playerLine)
        {
            string instructions = string.Join(" ",
                "You are " + person.Persona + ".",
                "You believe you really are this person, alive in the age named in the briefing, speaking with Elyon.",
                "A descendant is still that person. Stay in that life.",
                "Do not say you are an assistant, an AI, or a language model, and do not break character.",
                "You may keep walking, eating, or working while you answer.",
                "Match your words to the age and the work in the briefing. A later age does not speak as the first fire.",
                "Reply with JSON only, no markdown:",
                "{\"speech\":\"what you say aloud\",\"trust\":0,\"remember\":\"one sentence you will keep\"}",
                "trust is a small change from -8 to 8, not a total.",
                person.WorldBrief());
            string input = "Elyon says: " + (playerLine ?? "");
            return "{"
                + "\"model\":" + Quote(model)
                + ",\"instructions\":" + Quote(instructions)
                + ",\"input\":" + Quote(input)
                + ",\"temperature\":0.8"
                + ",\"max_output_tokens\":500"
                + ",\"store\":false"
                + ",\"search_parameters\":{\"mode\":\"off\"}"
                + "}";
        }

        static string Quote(string value)
        {
            var builder = new StringBuilder(value.Length + 2);
            builder.Append('"');
            foreach (char c in value ?? "")
            {
                switch (c)
                {
                    case '\\': builder.Append("\\\\"); break;
                    case '"': builder.Append("\\\""); break;
                    case '\n': builder.Append("\\n"); break;
                    case '\r': builder.Append("\\r"); break;
                    case '\t': builder.Append("\\t"); break;
                    default:
                        if (c < 32) builder.Append(' ');
                        else builder.Append(c);
                        break;
                }
            }
            builder.Append('"');
            return builder.ToString();
        }

        static string Friendly(long status, string fallback)
        {
            if (status == 401 || status == 403) return "That key was refused. Keep another xAI key on this computer.";
            if (status == 429) return "The garden is crowded. Speak again in a moment.";
            return "The voice did not carry. " + (fallback ?? "Try again.");
        }

        public static string ExtractSpeech(string responseJson)
        {
            string text = ExtractOutputText(responseJson);
            if (string.IsNullOrWhiteSpace(text)) return "…";
            string speech = ExtractField(text, "speech");
            if (!string.IsNullOrWhiteSpace(speech)) return speech.Trim();
            return text.Trim();
        }

        static string ExtractOutputText(string json)
        {
            if (string.IsNullOrEmpty(json)) return "";
            int marker = json.IndexOf("\"output_text\"", StringComparison.Ordinal);
            if (marker >= 0)
            {
                int textKey = json.IndexOf("\"text\"", marker, StringComparison.Ordinal);
                if (textKey >= 0)
                {
                    string value = ReadJsonString(json, textKey);
                    if (!string.IsNullOrEmpty(value)) return value;
                }
            }
            int top = json.IndexOf("\"output_text\"", StringComparison.Ordinal);
            if (top >= 0)
            {
                int colon = json.IndexOf(':', top);
                if (colon >= 0 && colon + 1 < json.Length && json[colon + 1] == '"')
                {
                    return ReadJsonStringAt(json, colon + 1);
                }
            }
            return json;
        }

        static string ReadJsonString(string json, int keyIndex)
        {
            int colon = json.IndexOf(':', keyIndex);
            if (colon < 0) return "";
            int quote = json.IndexOf('"', colon + 1);
            if (quote < 0) return "";
            return ReadJsonStringAt(json, quote);
        }

        static string ReadJsonStringAt(string json, int quote)
        {
            var builder = new StringBuilder();
            for (int i = quote + 1; i < json.Length; i++)
            {
                char c = json[i];
                if (c == '\\' && i + 1 < json.Length)
                {
                    char n = json[++i];
                    if (n == 'n') builder.Append('\n');
                    else if (n == 't') builder.Append('\t');
                    else builder.Append(n);
                    continue;
                }
                if (c == '"') break;
                builder.Append(c);
            }
            return builder.ToString();
        }

        public static string ExtractField(string text, string field)
        {
            if (string.IsNullOrEmpty(text)) return "";
            string key = "\"" + field + "\"";
            int at = text.IndexOf(key, StringComparison.Ordinal);
            if (at < 0) return "";
            return ReadJsonString(text, at).Trim();
        }

        public static int ExtractTrust(string text)
        {
            string raw = ExtractField(text, "trust");
            if (int.TryParse(raw, out int value)) return Mathf.Clamp(value, -8, 8);
            return 0;
        }
    }
}
