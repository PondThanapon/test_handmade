using UnityEngine;
using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;

// Minimal end-to-end sample:
// - Connects to Python via TCP
// - Sends webcam frames as JPG with a 4-byte little-endian length prefix
// - Receives hand JSON responses from the same TCP connection (also length-prefixed)
//
// Python side: set SEND_MODE=tcp and ensure IMG_BIND_PORT matches.
// Example (docker): SEND_MODE=tcp docker compose up --build
public class HandTcpCameraStreamer : MonoBehaviour
{
    [Header("Server")]
    public string serverHost = "127.0.0.1";
    public int serverPort = 5055;

    [Header("Camera")]
    public int targetFps = 20;
    public int jpegQuality = 70;

    TcpClient client;
    NetworkStream stream;
    Thread recvThread;
    volatile bool running;

    WebCamTexture webcam;
    Texture2D frameTexture;
    float nextSendTime;

    [Serializable]
    public class HandData
    {
        public int x;
        public int y;
        public float pinch;
    }

    [Serializable]
    public class Packet
    {
        public HandData left;
        public HandData right;
    }

    public HandData left;
    public HandData right;

    volatile bool hasNewJson;
    string latestJson;
    long receivedPackets;

    public long ReceivedPackets => receivedPackets;

    public bool TryConsumeLatestJson(out string json)
    {
        if (!hasNewJson)
        {
            json = null;
            return false;
        }

        hasNewJson = false;
        json = latestJson;
        return true;
    }

    void Start()
    {
        try
        {
            client = new TcpClient();
            client.NoDelay = true;
            client.Connect(serverHost, serverPort);
            stream = client.GetStream();
        }
        catch (Exception ex)
        {
            Debug.LogError($"TCP connect failed: {ex.Message}");
            enabled = false;
            return;
        }

        webcam = new WebCamTexture();
        webcam.Play();

        running = true;
        recvThread = new Thread(RecvLoop);
        recvThread.IsBackground = true;
        recvThread.Start();

        Debug.Log($"HandTcpCameraStreamer connected to {serverHost}:{serverPort}");
    }

    void Update()
    {
        if (!running || stream == null)
            return;

        if (TryConsumeLatestJson(out var json))
        {
            try
            {
                var packet = JsonUtility.FromJson<Packet>(json);
                left = packet != null ? packet.left : null;
                right = packet != null ? packet.right : null;
                Debug.Log("HAND JSON: " + json);
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to parse hand JSON: {ex.Message} | raw={json}");
            }
        }

        if (targetFps <= 0)
            return;

        if (Time.unscaledTime < nextSendTime)
            return;

        if (webcam == null || !webcam.isPlaying || webcam.width <= 16)
            return;

        nextSendTime = Time.unscaledTime + (1f / targetFps);

        try
        {
            EnsureFrameTexture(webcam.width, webcam.height);
            frameTexture.SetPixels32(webcam.GetPixels32());
            frameTexture.Apply(false);

            byte[] jpg = frameTexture.EncodeToJPG(Mathf.Clamp(jpegQuality, 1, 100));
            SendLengthPrefixed(jpg);
        }
        catch (Exception ex)
        {
            Debug.LogError($"Send frame failed: {ex.Message}");
            running = false;
        }
    }

    void EnsureFrameTexture(int width, int height)
    {
        if (frameTexture != null && frameTexture.width == width && frameTexture.height == height)
            return;

        frameTexture = new Texture2D(width, height, TextureFormat.RGB24, false);
    }

    void SendLengthPrefixed(byte[] payload)
    {
        if (payload == null)
            return;

        byte[] len = BitConverter.GetBytes(payload.Length);
        if (!BitConverter.IsLittleEndian)
            Array.Reverse(len);

        stream.Write(len, 0, 4);
        stream.Write(payload, 0, payload.Length);
        stream.Flush();
    }

    void RecvLoop()
    {
        try
        {
            while (running)
            {
                byte[] lenBytes = ReadExact(4);
                if (lenBytes == null)
                    break;

                if (!BitConverter.IsLittleEndian)
                    Array.Reverse(lenBytes);

                int len = BitConverter.ToInt32(lenBytes, 0);
                if (len <= 0 || len > 1_000_000)
                    continue;

                byte[] jsonBytes = ReadExact(len);
                if (jsonBytes == null)
                    break;

                latestJson = Encoding.UTF8.GetString(jsonBytes);
                hasNewJson = true;
                receivedPackets++;
            }
        }
        catch
        {
            // ignore
        }
        finally
        {
            running = false;
        }
    }

    byte[] ReadExact(int size)
    {
        byte[] buffer = new byte[size];
        int offset = 0;

        while (offset < size && running)
        {
            int read = stream.Read(buffer, offset, size - offset);
            if (read <= 0)
                return null;
            offset += read;
        }

        return buffer;
    }

    void OnDestroy()
    {
        running = false;
        try { stream?.Close(); } catch { }
        try { client?.Close(); } catch { }
        try { recvThread?.Join(200); } catch { }
        try { webcam?.Stop(); } catch { }
    }
}
