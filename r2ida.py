import idaapi
import idautils
import idc
import ida_kernwin
import ida_nalt
import r2pipe
import json
from idaapi import decompile

class R2PipeConsole(idaapi.PluginForm):
    def OnCreate(self, form):
        self.parent = self.FormToPyQtWidget(form)
        # Abrir r2pipe con el archivo actual de IDA
        base_address = idaapi.get_imagebase()
        print('r2 opening ', ida_nalt.get_input_file_path(), 'at base', hex(base_address))
        self.r2 = r2pipe.open(ida_nalt.get_input_file_path(), flags=['-m', hex(base_address)])
        print('r2 analyzing binary')
        self.r2.cmd("aaaa")
        self.sync_function_names()
        self.init_ui()

    def sync_function_names(self):
        for func_ea in idautils.Functions():
            name = idc.get_func_name(func_ea)
            # Asegurarse de que el nombre no contenga espacios o caracteres problemáticos
            safe_name = name.replace(" ", "_")
            # Ejecutar el comando en radare2
            cmd = f"afn {safe_name} {hex(func_ea)}"
            try:
                self.r2.cmd(cmd)
            except Exception as e:
                self.output.append(f"sync error {safe_name} in {hex(func_ea)}: {e}")

    def init_ui(self):
        try:
            from PyQt5 import QtWidgets, QtCore
        except ImportError:
            from PySide2 import QtWidgets, QtCore

        layout = QtWidgets.QVBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()

        self.output = QtWidgets.QTextEdit()
        self.output.setReadOnly(True)

        self.input = QtWidgets.QLineEdit()
        self.input.returnPressed.connect(self.send_command)

        self.button1 = QtWidgets.QPushButton("sync names")
        self.button1.clicked.connect(self.on_sync_names)
        self.button2 = QtWidgets.QPushButton("sync subview")
        self.button2.clicked.connect(self.on_sync_subview)

        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)

        layout.addWidget(self.output)
        layout.addWidget(self.input)
        layout.addLayout(button_layout)

        self.parent.setLayout(layout)

    def on_sync_names(self):
        self.sync_function_names()
        self.output.append("sync done.")

    def on_sync_subview(self):
        ida_kernwin.jumpto(int(self.r2.cmd("s")[2:],16))


    def send_command(self):
        cmd = self.input.text()
        if cmd:
            if cmd == 'ida':
                addr = int(self.r2.cmd('s')[2:],16)
                self.output.append('> ida')
                self.output.append(str(decompile(addr)))
            elif cmd == 'cls':
                self.output.clear()
            else:
                try:
                    result = self.r2.cmd(cmd)
                    self.output.append("> {}".format(cmd))
                    self.output.append(result)
                except Exception as e:
                    self.output.append("Error: {}".format(e))
            self.input.clear()

    def OnClose(self, form):
        self.r2.quit()

def show_r2pipe_console():
    global console
    try:
        console
    except NameError:
        console = R2PipeConsole()
    console.Show("Radare2")

class R2PipePlugin(idaapi.plugin_t):
    flags = idaapi.PLUGIN_UNL
    comment = "Plugin de consola"
    help = "Proporciona una consola para interactuar con radare2 mediante r2pipe"
    wanted_name = "Radare2"
    wanted_hotkey = "Ctrl-Shift-R"

    def init(self):
        # Definir el nombre único de la acción
        self.action_name = "r2pipe:console_action"

        # Crear una descripción de la acción
        self.action_desc = ida_kernwin.action_desc_t(
            self.action_name,         # Nombre de la acción
            "Consola",                # Texto que aparece en el menú
            self.ActionHandler(),     # Manejador de la acción
            self.wanted_hotkey,       # Atajo de teclado
            self.comment              # Comentario
        )

        # Registrar la acción
        ida_kernwin.register_action(self.action_desc)

        # Adjuntar la acción al menú "Edit/Plugins"
        ida_kernwin.attach_action_to_menu(
            "Edit/Plugins/Consola",    # Ruta del menú donde se añadirá la acción
            self.action_name,          # Nombre de la acción
            ida_kernwin.SETMENU_APP    # Bandera para indicar dónde insertar la acción
        )

        return idaapi.PLUGIN_OK

    def run(self, arg):
        show_r2pipe_console()

    def term(self):
        # Desregistrar la acción al terminar el plugin
        ida_kernwin.unregister_action(self.action_name)

    class ActionHandler(idaapi.action_handler_t):
        def __init__(self):
            idaapi.action_handler_t.__init__(self)

        # Este método se llama cuando la acción es activada
        def activate(self, ctx):
            show_r2pipe_console()
            return 1

        # Este método determina cuándo está disponible la acción
        def update(self, ctx):
            return idaapi.AST_ENABLE_ALWAYS

def PLUGIN_ENTRY():
    return R2PipePlugin()
