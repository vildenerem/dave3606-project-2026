import struct
import sys


def read_length_prefixed_string(f):
    length_bytes = f.read(4)
    if len(length_bytes) < 4:
        raise Exception("Unexpected end of file while reading string length")

    length = struct.unpack("I", length_bytes)[0]
    data = f.read(length)

    if len(data) < length:
        raise Exception("Unexpected end of file while reading string data")

    return data.decode("utf-8")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 read_set_binary.py <file_path>")
        return

    file_path = sys.argv[1]

    with open(file_path, "rb") as f:
        set_id = read_length_prefixed_string(f)
        set_name = read_length_prefixed_string(f)

        brick_count_bytes = f.read(4)
        if len(brick_count_bytes) < 4:
            raise Exception("Unexpected end of file while reading number of bricks")

        brick_count = struct.unpack("I", brick_count_bytes)[0]

        print(f"Set id: {set_id}")
        print(f"Set name: {set_name}")
        print("Inventory:")

        for i in range(brick_count):
            brick_type_id = read_length_prefixed_string(f)

            color_id_bytes = f.read(4)
            count_bytes = f.read(4)

            if len(color_id_bytes) < 4 or len(count_bytes) < 4:
                raise Exception("Unexpected end of file while reading brick data")

            color_id = struct.unpack("I", color_id_bytes)[0]
            count = struct.unpack("I", count_bytes)[0]

            print(
                f"  Brick {i + 1}: brick_type_id={brick_type_id}, color_id={color_id}, count={count}"
            )


if __name__ == "__main__":
    main()