using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class HandUDPReceiver : MonoBehaviour
{
    public int listenPort = 5052;

    UdpClient udp;
    Thread thread;

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
        udp = new UdpClient(listenPort);
        thread = new Thread(ReceiveLoop);
        thread.Start();

        Debug.Log("HandUDPReceiver started");
    }

    void ReceiveLoop()
    {
        IPEndPoint ep = new IPEndPoint(IPAddress.Any, listenPort);

        while (true)
        {
            byte[] data = udp.Receive(ref ep);
            string json = Encoding.UTF8.GetString(data);

            Packet packet = JsonUtility.FromJson<Packet>(json);

            left = packet.left;
            right = packet.right;
            Debug.Log("RAW JSON: " + json);


        }
    }

    void OnDestroy()
    {
        thread?.Abort();
        udp?.Close();
    }
}
