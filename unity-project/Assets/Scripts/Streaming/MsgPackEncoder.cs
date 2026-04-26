using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace SlopePoke.Streaming
{
    /// <summary>
    /// Minimal msgpack encoder covering the subset Slope-Poke metadata uses:
    /// nil, bool, int, float64, string, array, map. No streaming, no extension types.
    /// Pulled in as a single file to avoid a NuGet dependency in the Unity project.
    /// </summary>
    public static class MsgPackEncoder
    {
        public static byte[] Encode(object value)
        {
            using var ms = new MemoryStream();
            using var bw = new BinaryWriter(ms);
            WriteValue(bw, value);
            return ms.ToArray();
        }

        static void WriteValue(BinaryWriter bw, object v)
        {
            switch (v)
            {
                case null: bw.Write((byte)0xc0); return;
                case bool b: bw.Write(b ? (byte)0xc3 : (byte)0xc2); return;
                case string s: WriteString(bw, s); return;
                case byte u8: WriteInt(bw, u8); return;
                case short i16: WriteInt(bw, i16); return;
                case int i32: WriteInt(bw, i32); return;
                case long i64: WriteInt(bw, i64); return;
                case float f32: WriteFloat64(bw, f32); return;
                case double f64: WriteFloat64(bw, f64); return;
                case IDictionary dict: WriteMap(bw, dict); return;
                case IEnumerable arr: WriteArray(bw, arr); return;
                default:
                    throw new InvalidOperationException($"Unsupported msgpack type {v.GetType()}");
            }
        }

        static void WriteString(BinaryWriter bw, string s)
        {
            var bytes = Encoding.UTF8.GetBytes(s);
            int len = bytes.Length;
            if (len <= 31) bw.Write((byte)(0xa0 | len));
            else if (len <= 0xff) { bw.Write((byte)0xd9); bw.Write((byte)len); }
            else if (len <= 0xffff) { bw.Write((byte)0xda); WriteUInt16BE(bw, (ushort)len); }
            else { bw.Write((byte)0xdb); WriteUInt32BE(bw, (uint)len); }
            bw.Write(bytes);
        }

        static void WriteInt(BinaryWriter bw, long v)
        {
            if (v >= 0 && v <= 0x7f) { bw.Write((byte)v); return; }
            if (v < 0 && v >= -32) { bw.Write((byte)(0xe0 | (v & 0x1f))); return; }
            if (v >= sbyte.MinValue && v <= sbyte.MaxValue) { bw.Write((byte)0xd0); bw.Write((sbyte)v); return; }
            if (v >= short.MinValue && v <= short.MaxValue) { bw.Write((byte)0xd1); WriteInt16BE(bw, (short)v); return; }
            if (v >= int.MinValue && v <= int.MaxValue) { bw.Write((byte)0xd2); WriteInt32BE(bw, (int)v); return; }
            bw.Write((byte)0xd3); WriteInt64BE(bw, v);
        }

        static void WriteFloat64(BinaryWriter bw, double v)
        {
            bw.Write((byte)0xcb);
            var bits = BitConverter.DoubleToInt64Bits(v);
            WriteInt64BE(bw, bits);
        }

        static void WriteArray(BinaryWriter bw, IEnumerable arr)
        {
            var items = new List<object>();
            foreach (var x in arr) items.Add(x);
            int n = items.Count;
            if (n <= 15) bw.Write((byte)(0x90 | n));
            else if (n <= 0xffff) { bw.Write((byte)0xdc); WriteUInt16BE(bw, (ushort)n); }
            else { bw.Write((byte)0xdd); WriteUInt32BE(bw, (uint)n); }
            foreach (var x in items) WriteValue(bw, x);
        }

        static void WriteMap(BinaryWriter bw, IDictionary dict)
        {
            int n = dict.Count;
            if (n <= 15) bw.Write((byte)(0x80 | n));
            else if (n <= 0xffff) { bw.Write((byte)0xde); WriteUInt16BE(bw, (ushort)n); }
            else { bw.Write((byte)0xdf); WriteUInt32BE(bw, (uint)n); }
            foreach (DictionaryEntry kv in dict)
            {
                WriteValue(bw, kv.Key);
                WriteValue(bw, kv.Value);
            }
        }

        static void WriteUInt16BE(BinaryWriter bw, ushort v) { bw.Write((byte)(v >> 8)); bw.Write((byte)(v & 0xff)); }
        static void WriteUInt32BE(BinaryWriter bw, uint v)   { bw.Write((byte)(v >> 24)); bw.Write((byte)(v >> 16)); bw.Write((byte)(v >> 8)); bw.Write((byte)(v & 0xff)); }
        static void WriteInt16BE(BinaryWriter bw, short v)   => WriteUInt16BE(bw, (ushort)v);
        static void WriteInt32BE(BinaryWriter bw, int v)     => WriteUInt32BE(bw, (uint)v);
        static void WriteInt64BE(BinaryWriter bw, long v)
        {
            for (int i = 7; i >= 0; i--) bw.Write((byte)((v >> (i * 8)) & 0xff));
        }
    }
}
