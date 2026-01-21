using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System;

// Receives UDP JSON packets from Python hand-tracker.
// Notes:
// - Unity APIs (Debug.Log, scene objects) should be touched on main thread.
// - If another process (e.g. `nc -u -l 5052`) is already bound to the same port,
//   this receiver won't start.

public class HandUDPReceiver : MonoBehaviour
{
    public int listenPort = 5052;

    public enum ReceiveMode
    {
        UDP,
        TCPViaHandTcpCameraStreamer,
    }

    [Header("Mode")]
    public ReceiveMode receiveMode = ReceiveMode.UDP;

    [Tooltip("Assign the component that receives TCP hand JSON (e.g. HandTcpCameraStreamer).")]
    public HandTcpCameraStreamer tcpSource;

    UdpClient udp;
    Thread thread;

    volatile bool running;
    volatile bool hasNewPacket;
    string latestJson;
    IPEndPoint lastSender;

    public HandData left;
    public HandData right;

    [System.Serializable]
    public class HandData
    {
        public int x;
        public int y;
        public float pinch;
    }

    [System.Serializable]
    class Packet
    {
        public HandData left;
        public HandData right;
    }

    void Start()
    {
        if (receiveMode == ReceiveMode.TCPViaHandTcpCameraStreamer)
        {
            Debug.Log("HandUDPReceiver running in TCP adapter mode");
            return;
        }

        try
        {
            // Bind explicitly to IPv4 to avoid IPv6-only binding issues on some platforms.
            udp = new UdpClient(AddressFamily.InterNetwork);
            udp.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            udp.Client.Bind(new IPEndPoint(IPAddress.Any, listenPort));
        }
        catch (Exception ex)
        {
            Debug.LogError($"HandUDPReceiver failed to bind UDP port {listenPort}: {ex.Message}");
            enabled = false;
            return;
        }

        running = true;
        thread = new Thread(ReceiveLoop);
        thread.IsBackground = true;
        thread.Start();

        Debug.Log($"HandUDPReceiver started (listening UDP {listenPort})");
    }

    void ReceiveLoop()
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, 0);

        while (running)
        {
            try
            {
                byte[] data = udp.Receive(ref ep);
                string json = Encoding.UTF8.GetString(data).Trim();
                if (string.IsNullOrEmpty(json))
                    continue;

                latestJson = json;
                lastSender = new IPEndPoint(ep.Address, ep.Port);
                hasNewPacket = true;
            }
            catch (SocketException)
            {
                // Usually thrown when udp is closed.
                break;
            }
            catch (Exception)
            {
                // Keep receiver alive on transient errors.
            }
        }
    }

    void Update()
    {
        if (receiveMode == ReceiveMode.TCPViaHandTcpCameraStreamer)
        {
            if (tcpSource == null)
                return;

            // Copy values from TCP source into this component's HandData type.
            if (tcpSource.left != null)
            {
                left = new HandData { x = tcpSource.left.x, y = tcpSource.left.y, pinch = tcpSource.left.pinch };
            }
            else
            {
                left = null;
            }

            if (tcpSource.right != null)
            {
                right = new HandData { x = tcpSource.right.x, y = tcpSource.right.y, pinch = tcpSource.right.pinch };
            }
            else
            {
                right = null;
            }

            return;
        }

        if (!hasNewPacket)
            return;

        hasNewPacket = false;
        string json = latestJson;

        try
        {
            Packet packet = JsonUtility.FromJson<Packet>(json);
            left = packet?.left;
            right = packet?.right;

            string sender = lastSender != null ? $"{lastSender.Address}:{lastSender.Port}" : "unknown";
            Debug.Log($"RAW JSON ({sender}): {json}");
        }
        catch (Exception ex)
        {
            Debug.LogError($"Failed to parse JSON: {ex.Message} | raw={json}");
        }
    }

    void OnDestroy()
    {
        running = false;
        try { udp?.Close(); } catch { }
        try { thread?.Join(200); } catch { }
    }
}
