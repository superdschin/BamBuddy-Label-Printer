from niimbot_b1 import NiimbotB1Printer

def print_label(image):
    printer = None
    try:
        printer = NiimbotB1Printer.connect_saved_or_auto(timeout_s=10.0, debug=False, save_found=True)
        return printer.print_image(image, density=3, copies=1, row_delay_s=0.012)
    finally:
        if printer is not None:
            printer.disconnect()


