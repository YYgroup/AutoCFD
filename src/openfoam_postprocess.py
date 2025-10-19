import httpx
from mcp.server import FastMCP
import subprocess
import time as time_pkg
import logging
import os

from utils.util import *

from postprocess import *

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
# 创建 logger 实例
logger = logging.getLogger(__name__)

# 初始化 FastMCP 服务器
app = FastMCP('openfoam-postprocess')

#################################################################################################################################
# 常用参数描述
latestTime_description = "latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False."

time_description = "time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used."

case_dir_description = "case_dir (str, optional): The case directory. Defaults to '.'."

fields_description = "fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'"

field_optional_description = "field (str, optional): Name of the operand field. Defaults to ''. For example: 'U', etc."

field_description = "field (str): Name of the operand field. Defaults to ''. For example: 'U', etc."

patches_description = "patches (str): A space-separated list of patch names. For example: 'patch1 patch2', 'patch1', etc."

#################################################################################################################################

@app.tool()
def blockMesh() -> str:
    """
    Do meshing on blockMeshDict in OpenFOAM.

    Args:
        None
    """
    return "blockMesh"


# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                  工厂函数                                                                     #
# --------------------------------------------------------------------------------------------------------------------------------------------- #
# 不需要指定 field 
def generate_function(func_name: str, description: str):
    """Factory function to create @app.tool decorated postProcess functions"""
    
    # 先定义基础函数
    def implementation(latestTime: bool = False, time: str = "") -> str:
        """
        {description}

        Args:
            latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
            time (str, optional): Specifies the range of time steps to process. 
                                For example: ':100, 120, 160:200, 300:', 'none', etc. 
                                Default is an empty string, meaning this option is not used.
        """
        command = f"postProcess -func {func_name}"
        if latestTime:
            command += " -latestTime"
        if time:
            command += f" -time '{time}'"

        return command

    # 设置函数元数据
    implementation.__name__ = f"postProcess_{func_name}"
    implementation.__doc__ = implementation.__doc__.format(description=description, func_name=func_name)
    
    # 最后应用装饰器
    return app.tool()(implementation)

# 需要指定 fields 
def generate_function_with_fields(func_name: str, description: str):
    """Factory function to create @app.tool decorated postProcess functions"""
    
    # 先定义基础函数
    def implementation(latestTime: bool = False, time: str = "", fields: str = "") -> str:
        """
        {description}

        Args:
            latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
            time (str, optional): Specifies the range of time steps to process. 
                                For example: ':100, 120, 160:200, 300:', 'none', etc. 
                                Default is an empty string, meaning this option is not used.
            fields (str): A comma-separated list of field names to be computed.
                      For example: 'U, V', etc.
        """
        field_list = [f.strip() for f in fields.split(",")]
        if len(field_list) < 1:
            raise ValueError("At least one field must be specified for the operation.")
        command = f"postProcess -func '{func_name}({','.join(field_list)})'"
        if latestTime:
            command += " -latestTime"
        if time:
            command += f" -time '{time}'"

        return command

    # 设置函数元数据
    implementation.__name__ = f"postProcess_{func_name}"
    implementation.__doc__ = implementation.__doc__.format(description=description, func_name=func_name)
    
    # 最后应用装饰器
    return app.tool()(implementation)

# 需要指定 field
def generate_function_with_field(func_name: str, description: str):
    """Factory function to create @app.tool decorated postProcess functions"""
    
    # 先定义基础函数
    def implementation(latestTime: bool = False, time: str = "", field: str = "") -> str:
        """
        {description}

        Args:
            latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
            time (str, optional): Specifies the range of time steps to process. 
                                For example: ':100, 120, 160:200, 300:', 'none', etc. 
                                Default is an empty string, meaning this option is not used.
            field (str, optional): Name of the operand field. Defaults to "".
                      For example: 'U', etc.
        """

        command = f"postProcess -func '{func_name}({field})'"

        if latestTime:
            command += " -latestTime"
        if time:
            command += f" -time '{time}'"

        return command

    # 设置函数元数据
    implementation.__name__ = f"postProcess_{func_name}"
    implementation.__doc__ = implementation.__doc__.format(description=description, func_name=func_name)
    
    # 最后应用装饰器
    return app.tool()(implementation)



# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                         基础物理量与标量/矢量运算                                                             #
# --------------------------------------------------------------------------------------------------------------------------------------------- #


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# add
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_add(latestTime: bool = False, time: str = "", fields: str = "") -> str:
    """
    Post-processing function to sum a given list of (at least two or more) fields in OpenFOAM, where the fields possess the same sizes and dimensions.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. Contains at least two fields to be summed.
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A comma-separated list of field names to be summed.
                      For example: 'U, V', etc.
    """
    if fields.split(",") < 2:
        raise ValueError("At least two fields must be specified.")
    command = f"postProcess -func 'add({fields})'"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# subtract
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_subtract(latestTime: bool = False, time: str = "", fields: str = "") -> str:
    """
    Post-processing function to subtract two fields in OpenFOAM. The operation is: field1 - field2.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        fields (str): A comma-separated list of exactly two field names to be subtracted.
                      For example: 'U, V', etc.
    """
    field_list = [f.strip() for f in fields.split(",")]
    if len(field_list) != 2:
        raise ValueError("Exactly two fields must be specified for subtraction.")
    
    command = f"postProcess -func 'subtract({field_list[0]}, {field_list[1]})'"
    
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# magSqr
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_magSqr(latestTime: bool = False, time: str = "", field: str = "") -> str:
    """
    Post-processing function to compute the magnitude squared of a given field in OpenFOAM.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        field (str): The name of the field for which to compute the magnitude squared.
    """
    if not field:
        raise ValueError("A field must be specified for computing magnitude squared.")
    
    command = f"postProcess -func 'magSqr({field})'"
    
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# mag
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_mag(latestTime: bool = False, time: str = "", field: str = "") -> str:
    """
    Post-processing function to compute the magnitude of a given vector field in OpenFOAM.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        field (str): The name of the vector field for which to compute the magnitude.
    """
    if not field:
        raise ValueError("A field must be specified for computing magnitude.")
    
    command = f"postProcess -func 'mag({field})'"
    
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    logger.info("sleep 5 seconds starting...")
    time_pkg.sleep(5)  # Simulate some processing time
    logger.info("sleep 5 seconds finished.")
    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# components
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_components(
    latestTime: bool = False,
    time: str = "",
    field: str = ""
) -> str:
    """
    Post-processing function to extract the components of a given vector or tensor field in OpenFOAM.

    This function generates scalar fields for each component of the input field. 
    Supported types include vector, sphericalTensor, symmTensor, and tensor.
    
    Output field names are automatically generated using standard suffixes:
        - vector/sphericalTensor: x, y, z
        - symmTensor: xx, xy, xz, yy, yz, zz
        - tensor: xx, xy, xz, yx, yy, yz, zx, zy, zz

    Args:
        latestTime (bool, optional): Whether to process only the last available time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        field (str): The name of the input field from which to extract components.
                     Must be a non-scalar field (e.g., "U", "tau", etc.)
    """
    if not field:
        raise ValueError("An input field must be specified for the components operation.")

    # 构造基本命令
    command = f"postProcess -func 'components({field})'"

    # 时间相关选项
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# log
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_log(
    latestTime: bool = False,
    time: str = "",
    case_dir: str = "",
    field: str = "",
    clip: float = 1e-3,
    scale: float = 1.0,
    offset: float = 0.0
) -> str:    
    r"""
    Computes the natural logarithm of an input \c volScalarField.

    \f[
        f = s \ln(max(f_0, a)) + t
    \f]

    where
    \vartable
      f     | Output volScalarField
      f_0   | Input volScalarField
      \ln   | Natural logarithm operator
      a     | Clip scalar
      s     | Scaling factor
      t     | Offset factor
    \endvartable

    Args:
        field (str): Name of the operand field. Defaults to ''. For example: 'U', etc.
        clip (float, optional): Clip values below this threshold to prevent log(0) or negative values.
                                 Defaults to 1e-3.
        scale (float, optional): Scaling factor applied before computing the logarithm. Defaults to 1.0.
        offset (float, optional): Offset factor added to the field before scaling. Defaults to 0.0.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "log"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            log;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entry (runtime modifiable)
    field           {field};

    // Optional entries (runtime modifiable)
    clip            {clip};
    checkDimensions false;
    scale           {scale};
    offset          {offset};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# pow
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_pow(latestTime: bool = False, time: str = "", case_dir: str = "", field: str = "", n: int = 4, scale: float = 1.0, offset: float = 0.0) -> str:
    r"""
    Computes the power of an input volScalarField.

    Args:
        field (str): Name of the operand field. Defaults to ''. For example: 'U', etc.
        n (int): Number of power.
        scale (float): Scaling factor. 
        offset (float): Offset factor. 
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "pow"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            pow;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entry (runtime modifiable)
    field           {field};
    n               {n};

    // Optional entries (runtime modifiable)
    checkDimensions false;
    scale           {scale};
    offset          {offset};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    pow             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# grad
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_grad(
    latestTime: bool = False,
    time: str = "",
    field: str = "",
    result: str = ""
) -> str:
    """
    Post-processing function to compute the gradient of a given scalar or vector field in OpenFOAM.

    The output is a volVectorField (if input is scalar)
    or a volTensorField (if input is vector).

    Args:
        latestTime (bool, optional): Whether to process only the last available time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        field (str): The name of the input field from which to compute the gradient.
                     Must be a scalar or vector field (e.g., "T", "U").
        result (str, optional): Optional name for the output field. If not provided, uses default naming.
    """
    if not field:
        raise ValueError("An input field must be specified for the grad operation.")

    # 构造基本命令
    command = f"postProcess -func 'grad({field})'"

    # 可选输出字段名
    if result:
        command += f" -result {result}"

    # 时间相关选项
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# ddt
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_ddt(
    latestTime: bool = False,
    time: str = "",
    case_dir: str = "",
    field: str = ""
) -> str:
    """
    Computes the Eulerian time derivative of an input volume field for time-variant simulations (not appropriate to steady-state simulations).

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        field (str): Name of the operand field. 
        case_dir (str): The case directory. Defaults to "".
    """
    
    func = "ddt"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            ddt;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entries (runtime modifiable)
    field           {field};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# ddt2
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_ddt2(latestTime: bool = False, time: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    Computes the magnitude or magnitude squared of the Eulerian time derivative of an input volume field for time-variant simulations
    (not appropriate to steady-state simulations).

    The result can be further used for determining e.g. variance or RMS values.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names.
                For example: 'omega k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "ddt2"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            ddt2;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields          ({fields});

    // Optional entries (unmodifiable)
    mag             false;

    // Optional entries (runtime modifiable)
    result          d@@dt2;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# div
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_div(
    latestTime: bool = False,
    time: str = "",
    field: str = ""
) -> str:
    """
    Computes the divergence of an input field.

    Args:
        latestTime (bool, optional): Whether to process only the last available time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc.
                              Default is an empty string, meaning this option is not used.
        field (str): The name of the input field from which to compute.
                     Must be a scalar or vector field (e.g., "T", "U").
    """
    if not field:
        raise ValueError("An input field must be specified for the div operation.")

    # 构造基本命令
    command = f"postProcess -func 'div({field})'"

    # 时间相关选项
    if latestTime:
        command += " -latestTime"
    if time:
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# norm
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_norm(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    field: str = "", 
    norm_type : str = "",
    p: int = 2, 
    divisor_num: int = 2,
    divisorField: str = ""
    ) -> str:
    r"""
    Normalises an input field with a chosen norm, and outputs a new normalised field.

    Args:
        field (str): Name of the operand field. For example: 'omega k', 'epsilon', etc.
        norm_type (str): The norm type to use. Can be one of:
                        - 'L1' (default): L1 norm (sum of absolute values)
                        - 'L2': L2 norm (square root of sum of squares)
                        - 'Lp': Lp norm (pth root of sum of powers)
                        - 'max': Maximum norm
                        - 'composite': Composite norm with Function1 divisor
                        - 'divisorField': Composite norm with divisorField
        p (int, optional): The p value for the Lp norm. Defaults to 2.0.
        divisor_num (int, optional): The number to divide by when using the composite norm.
        divisorField (str, optional): The name of the divisor field. 
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
    """
    
    func = "norm"
    func_id = get_func_id(func, case_dir)

    norm_content = ""
    if norm_type == 'L1' or norm_type == 'L2' or norm_type == 'max':
        norm_content = f'''
        norm            {norm_type};
        '''
    elif norm_type == 'Lp':
        norm_content = f'''
        norm            Lp;
        p               {p};
        '''
    elif norm_type == 'composite':
        norm_content = f'''
        norm            composite;
        divisor         constant {divisor_num};
        '''
    elif norm_type == 'divisorField':
        norm_content = f'''
        norm            composite;
        divisorField    {divisorField};
        '''

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries
    type            norm;
    libs            (fieldFunctionObjects);
    field           {field};
    {norm_content}

    // Inherited entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  writeTime;
    writeControl    writeTime;

    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# randomise
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_randomise(latestTime: bool = False, time: str = "", case_dir: str = "", magPerturbation: float = 0.1, field: str = "") -> str:
    """
    Adds a random component to an input field, with a specified perturbation magnitude.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
        magPerturbation (float): The magnitude of the perturbation. Defaults to 0.1.
        field (str): Name of the operand field. Defaults to "".
                     For example: "U", etc. 
        
    """

    if field == "":
        raise ValueError("One field must be specified for the operation.")

    func = "randomise"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Mandatory entries (runtime modifiable)
        magPerturbation {magPerturbation};

        // Mandatory (inherited) entries (runtime modifiable)
        field           {field};

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# fieldMinMax
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_fieldMinMax(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "") -> str:
    """
    Computes the values and locations of field minima and maxima.
    These are good indicators of calculation performance, e.g. to confirm that predicted results are within expected bounds, or how well a case is converging.
    Multiple fields can be processed, where for rank > 0 primitives, e.g. vectors and tensors, the extrema can be calculated per component, or by magnitude. In addition, spatial location and local processor index are included in the output.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
        magPerturbation (float): The magnitude of the perturbation. Defaults to 0.1.
        fields (str): A comma-separated list of field names to be computed.
                      For example: 'omega, k', 'epsilon', etc.
    """

    field_list = [f.strip() for f in fields.split(",")]
    if len(field_list) < 1:
        raise ValueError("At least one fields must be specified for the operation.")

    func = "fieldMinMax"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type        {func};
        libs        (fieldFunctionObjects);

        // Mandatory entries (runtime modifiable)
        mode        magnitude;
        fields      ({" ".join(field_list)});

        // Optional entries (runtime modifiable)
        location    true;

        // Optional (inherited) entries
        writePrecision  8;
        writeToFile     true;
        useUserTime     true;
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                            场计算与统计分析                                                                   #
# --------------------------------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# LambVector
# --------------------------------------------------------------------------------------------------------------------------------------------- #
postProcess_LambVector = generate_function("LambVector", "Post-processing function to compute Lamb Vector in OpenFOAM.")

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# Lambda2
# --------------------------------------------------------------------------------------------------------------------------------------------- #
Lambda2_description = '''
Computes the second largest eigenvalue of the sum of the square of
    the symmetrical and anti-symmetrical parts of the velocity gradient tensor.
'''
postProcess_Lambda2 = generate_function("Lambda2", Lambda2_description)

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# vorticity
# --------------------------------------------------------------------------------------------------------------------------------------------- #
postProcess_vorticity = generate_function("vorticity", "Post-processing function to compute vorticity criterion in OpenFOAM.")

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# Q
# --------------------------------------------------------------------------------------------------------------------------------------------- #
Q_description = r'''
Computes the second invariant of the velocity gradient tensor \f$[s^{-2}]\f$.

    \f[
        \vec Q = \frac{1}{2}
        [ (tr (\nabla \vec U) )^2
        - tr (\nabla \vec U \cdot \nabla \vec U) ]
    \f]

    where
    \vartable
        \vec U       | velocity [m/s]
    \endvartable
'''
postProcess_Q = generate_function("Q", Q_description)

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# flowType
# --------------------------------------------------------------------------------------------------------------------------------------------- #
flowType_description = r'''Computes the flow type indicator of an input velocity field.

    The flow type indicator is obtained according to the following equation:
    \f[
        \lambda = \frac{|D| - |\omega|}{|D| + |\omega|}
    \f]

    where
    \vartable
      \lambda | Flow type indicator
      D       | Symmetric part of the gradient tensor of velocity
      \omega  | Skew-symmetric part of the gradient tensor of velocity
    \endvartable

    The flow type indicator values mean:
    \verbatim
      -1 = rotational flow
       0 = simple shear flow
       1 = planar extensional flow
    \endverbatim
'''
postProcess_flowType = generate_function("flowType", flowType_description)

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# enstrophy
# --------------------------------------------------------------------------------------------------------------------------------------------- #
enstrophy_description = r'''Computes the enstrophy of an input \c volVectorField.

    Enstrophy, i.e. \f$\xi\f$:

    \f[
        \xi = 0.5 mag(\nabla \times \vec U )^2
    \f]

    where \f$\vec U\f$ is the input \c volVectorField.
'''
postProcess_enstrophy = generate_function_with_field("enstrophy", enstrophy_description)


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# turbulenceFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_turbulenceFields(latestTime: bool = False, time: str = "", fields: str = "", case_dir: str = "") -> str:
    """
    Computes the turbulence fields for a given velocity field.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A comma-separated list of field names to be computed.
                      For example: 'omega, k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to ".".

    """
    field_list = [f.strip() for f in fields.split(",")]
    if len(field_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -func 'turbulenceFields({','.join(field_list)})'"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# yPlus
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_yPlus(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    """
    Computes the yPlus for a given velocity field.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to ".".
    """
    
    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -func yPlus"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# energySpectrum
# --------------------------------------------------------------------------------------------------------------------------------------------- #
energySpectrum_description = "Calculates the energy spectrum for a box of turbulence."
postProcess_energySpectrum = generate_function("energySpectrum", energySpectrum_description)


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# XiReactionRate
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_XiReactionRate(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    """
    Writes the turbulent flame-speed and reaction-rate volScalarFields for the Xi-based combustion models.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
    """

    func = "XiReactionRate"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# wallShearStress
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_wallShearStress(latestTime: bool = False, time: str = "", case_dir: str = "", patch_names: str = "") -> str:
    """
    Computes the wall-shear stress at selected wall patches.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
        patch_names (str, optional): A comma-separated list of patch names to be processed.
                        For example: 'wall1, wall2', 'wall1', etc.
    """

    func = "wallShearStress"
    func_id = get_func_id(func, case_dir)

    patch_list = [f.strip() for f in patch_names.split(",")]
    if len(patch_list) > 1:
        function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Optional entries (runtime modifiable)
        patches         ({" ".join(patch_list)});

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''
    else:
        function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# wallHeatFlux
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_wallHeatFlux(latestTime: bool = False, time: str = "", case_dir: str = "", patch_names: str = "") -> str:
    """
    Computes the wall-heat flux at selected wall patches.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process.
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
        patch_names (str, optional): A comma-separated list of patch names to be processed.
                        For example: 'wall1, wall2', 'wall1', etc.
    """

    func = "wallHeatFlux"
    func_id = get_func_id(func, case_dir)

    patch_list = [f.strip() for f in patch_names.split(",")]
    if len(patch_list) > 1:
        function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Optional entries (runtime modifiable)
        patches         ({" ".join(patch_list)});
        qr          qr;

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''
    else:
        function_content = f'''
    {func_id}
    {{
        // Mandatory entries (unmodifiable)
        type            {func};
        libs            (fieldFunctionObjects);

        // Optional entries (runtime modifiable)
        qr          qr;

        // Optional (inherited) entries
        region          region0;
        enabled         true;
        log             true;
        timeStart       0;
        timeEnd         1000;
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                  无量纲数                                                                     #
# --------------------------------------------------------------------------------------------------------------------------------------------- #
# CourantNo, MachNo, PecletNo, ObukhovLength
CourantNo_description = "Computes the Courant number field for time-variant simulations."
postProcess_CourantNo = generate_function("CourantNo", CourantNo_description)

MachNo_description = r"Computes the Mach number as a \c volScalarField."
postProcess_MachNo = generate_function("MachNo", MachNo_description)

PecletNo_description = r"Computes the Peclet number as a \c surfaceScalarField."
postProcess_PecletNo = generate_function("PecletNo", PecletNo_description)

ObukhovLength_description = "Computes the Obukhov length field and associated friction velocity field."
postProcess_ObukhovLength = generate_function("ObukhovLength", ObukhovLength_description)


# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                               几何与网格操作                                                                  #
# --------------------------------------------------------------------------------------------------------------------------------------------- #
AMIWeights_description = "Computes the AMI weights for the given mesh."
postProcess_AMIWeights = generate_function("AMIWeights", AMIWeights_description)

writeCellCentres_description = r"Writes the cell-centres volVectorField and the three component fields as \c volScalarFields."
postProcess_writeCellCentres = generate_function("writeCellCentres", writeCellCentres_description)

writeCellVolumes_description = r"Writes the cell-volumes \c volScalarField."
postProcess_writeCellVolumes = generate_function("writeCellVolumes", writeCellVolumes_description)

processorField_description = r"Writes a scalar field whose value is the local processor ID. The output field name is \c processorID."
postProcess_processorField = generate_function("processorField", processorField_description)

# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                流函数和流线                                                                   #
# --------------------------------------------------------------------------------------------------------------------------------------------- #
streamFunction_description = "Computes the stream function."
postProcess_streamFunction = generate_function("streamFunction", streamFunction_description)

# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                  Sampling                                                                     #
# --------------------------------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# probes
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_probes(latestTime: bool = False, time: str = "", probeLocations: str = "", fields: str = "", case_dir: str = "") -> str:
    """
    Sample field values at point locations and writes the result to file.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        probeLocations (str): A comma-separated list of probe locations.
                      For example: '(0 1 0), (1 0 0)', '(1 0 0)', etc.
        fields (str): A comma-separated list of field names to sample.
                      For example: 'omega, k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to "".
    """

    fields_list = [f.strip() for f in fields.split(",")]
    if len(fields_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    probeLocations_list = [f.strip() for f in probeLocations.split(",")]
    if len(probeLocations_list) < 1:
        raise ValueError("At least one point must be specified for the operation.")
    
    func = "probes"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        // Mandatory entries
        type                {func};
        libs                (sampling);
        probeLocations      ({" ".join(probeLocations_list)});
        fields              ({" ".join(fields_list)});
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# patchProbes
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_patchProbes(latestTime: bool = False, time: str = "", probeLocations: str = "", fields: str = "", patches: str = "", case_dir: str = "") -> str:
    """
    Probe patch field values with probe locations and writes the result.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        probeLocations (str): A comma-separated list of probe locations.
                      For example: '(0 1 0), (1 0 0)', '(1 0 0)', etc.
        fields (str): A comma-separated list of field names to sample.
                      For example: 'omega, k', 'epsilon', etc.
        patches (str): A comma-separated list of patch names to sample.
                      For example: 'patch_1, patch_2', 'patch_1', etc.
        case_dir (str): The case directory. Defaults to "".
    """

    fields_list = [f.strip() for f in fields.split(",")]
    if len(fields_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    probeLocations_list = [f.strip() for f in probeLocations.split(",")]
    if len(probeLocations_list) < 1:
        raise ValueError("At least one probeLocations must be specified for the operation.")
    
    patches_list = [f.strip() for f in patches.split(",")]
    if len(patches_list) < 1:
        raise ValueError("At least one patches must be specified for the operation.")
    
    func = "patchProbes"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        // Mandatory entries
        type                {func};
        libs                (sampling);
        patches             ({" ".join(patches_list)});
        probeLocations      ({" ".join(probeLocations_list)});
        fields              ({" ".join(fields_list)});
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# points_uniform
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_points_uniform(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", start_point: str = "", end_point: str = "", axis: str = "", nPoints: int = 100) -> str:
    """
    uniformly distributed points on line between start and end points.

    Args:
        fields (str): A comma-separated list of field names to sample.
                      For example: 'omega, k', 'epsilon', etc.
        start_point (str): start point.
                      For example: '(0 1 0)', etc.
        end_point (str): end point.
                      For example: '(0 -1 0)', etc.
        axis (str): The representation of point coordinates in the output file.
                      For example: 'x', 'y', 'z', 'xyz', 'distance'.
        nPoints (int): The number of points to sample. Defaults to 100.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
    """
    fields_list = [f.strip() for f in fields.split(",")]
    if len(fields_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    func = "sets"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            sets;
        functionObjectLibs ("libsampling.so");
        setFormat       raw;
        
        fields              ({" ".join(fields_list)});
        
        sets
        {{
            mySet1
            {{
                type    uniform;
                axis    {axis};
                start   {start_point};
                end     {end_point};
                nPoints {nPoints};
            }}
        }}
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# points_cloud
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_points_cloud(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", points: str = "", axis: str = "") -> str:
    """
    The cloud set samples field values at list of point locations.

    Args:
        fields (str): A comma-separated list of field names to sample.
                      For example: 'omega, k', 'epsilon', etc.
        points (str): A comma-separated list of points.
                      For example: '(0 1 0), (1 0 0)', '(1 0 0)', etc.
        axis (str): The representation of point coordinates in the output file.
                      For example: 'x', 'y', 'z', 'xyz', 'distance'.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".

    """
    fields_list = [f.strip() for f in fields.split(",")]
    if len(fields_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    points_list = [f.strip() for f in points.split(",")]
    if len(points_list) < 1:
        raise ValueError("At least one inside point must be specified for the operation.")
    
    func = "sets"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            sets;
        libs            (sampling);
        setFormat       raw;
        
        fields              ({" ".join(fields_list)});
        
        sets
        {{
            mySet1
            {{
                type    cloud;
                axis    {axis};
                points  ({" ".join(points_list)});
            }}
        }}
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# points_shortestPath
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_points_shortestPath(latestTime: bool = False, time: str = "", insidePoints: str = "", outsidePoints: str = "", fields: str = "", axis: str = "", case_dir: str = "") -> str:
    """
    Finds shortest path (in terms of cell centres) to walk on mesh from any point in insidePoints to any point in outsidePoints.
    Sample the field on this specified point set.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        insidePoints (str): A comma-separated list of inside points.
                      For example: '(0 1 0), (1 0 0)', '(1 0 0)', etc.
        outsidePoints (str): A comma-separated list of outside points.
                      For example: '(0 1 0), (1 0 0)', '(1 0 0)', etc.
        fields (str): A comma-separated list of field names to sample.
                      For example: 'omega, k', 'epsilon', etc.
        axis (str): The representation of point coordinates in the output file.
                      For example: 'x', 'y', 'z', 'xyz', 'distance'.
        case_dir (str): The case directory. Defaults to "".
    """

    fields_list = [f.strip() for f in fields.split(",")]
    if len(fields_list) < 1:
        raise ValueError("At least one field must be specified for the operation.")
    
    insidePoints_list = [f.strip() for f in insidePoints.split(",")]
    if len(insidePoints_list) < 1:
        raise ValueError("At least one inside point must be specified for the operation.")
    
    outsidePoints_list = [f.strip() for f in outsidePoints.split(",")]
    if len(outsidePoints_list) < 1:
        raise ValueError("At least one outside point must be specified for the operation.")
    
    func = "sets"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            sets;
        libs            (sampling);
        setFormat       raw;
        
        fields              ({" ".join(fields_list)});
        
        sets
        {{
            mySet1
            {{
                type                shortestPath;
                axis                {axis};
                insidePoints        ({" ".join(insidePoints_list)});
                outsidePoints       ({" ".join(outsidePoints_list)});
            }}
        }}
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaces_cuttingPlane
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaces_cuttingPlane(latestTime: bool = False, time: str = "", point: str = "", normal: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    Constructs cutting plane through a mesh. Sample fields on this specified surface.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names to sample.
                      For example: 'omega k', 'epsilon', etc.
        point (str): A point.
                      For example: '(1 0 0)', etc.
        normal (str): A normal.
                      For example: '(1 0 0)', etc.
        case_dir (str): The case directory. Defaults to "".
    """
    fields = check_fields(fields)
    func = "surfaces"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            surfaces;
        libs            (sampling);
        surfaceFormat       raw;
        
        fields              ({fields});
        
        surfaces
        {{
            mySurfaces1
            {{
                type                cuttingPlane;
                point               {point};
                normal              {normal};
            }}
        }};
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaces_isoSurfaceCell
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaces_isoSurfaceCell(latestTime: bool = False, time: str = "", isoValue: str = "", isoField: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    A surface formed by the iso value. Sample fields on this specified surface.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names to sample.
                      For example: 'omega k', 'epsilon', etc.
        isoValue (str): iso value.
                      For example: '1', etc.
        isoField (str): iso field.
                      For example: 'p', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    fields = check_fields(fields)
    func = "surfaces"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            surfaces;
        libs            (sampling);
        surfaceFormat       raw;
        
        fields              ({fields});
        
        surfaces
        {{
            mySurfaces1
            {{
                type                isoSurfaceCell;
                isoField               {isoField};
                isoValue              {isoValue};
            }}
        }};
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaces_sampledIsoSurface
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaces_sampledIsoSurface(latestTime: bool = False, time: str = "", isoValue: str = "", isoField: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    A sampledSurface defined by a surface of iso value.
    It only recalculates the iso-surface if time changes.
    Sample fields on this specified surface.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names to sample.
                      For example: 'omega k', 'epsilon', etc.
        isoValue (str): iso value.
                      For example: '1', etc.
        isoField (str): iso field.
                      For example: 'p', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    fields = check_fields(fields)
    func = "surfaces"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            surfaces;
        libs            (sampling);
        surfaceFormat       raw;
        
        fields              ({fields});
        
        surfaces
        {{
            mySurfaces1
            {{
                type                isoSurface;
                isoField               {isoField};
                isoValue              {isoValue};
            }}
        }};
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaces_sampledPatch
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaces_sampledPatch(latestTime: bool = False, time: str = "", fields: str = "", patches: str = "", case_dir: str = "") -> str:
    r"""
    Sample fields on this specified surface or patch.
    
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names to sample.
                      For example: 'omega k', 'epsilon', etc.
        patches (str): A comma-separated list of patch names to sample.
                      For example: 'patch_1, patch_2', 'patch_1', etc.
        case_dir (str): The case directory. Defaults to "".
    """
    fields = check_fields(fields)
    func = "surfaces"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            surfaces;
        libs            (sampling);
        surfaceFormat       raw;
        
        fields              ({fields});
        
        surfaces
        {{
            mySurfaces1
            {{
                type        patch;
                patches     ({patches});
                interpolate false;
            }}
        }};
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                 lagrangian                                                                    #
# --------------------------------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# cloudInfo
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_cloudInfo(latestTime: bool = False, time: str = "", clouds: str = "", case_dir: str = "") -> str:
    r"""
    Outputs Lagrangian cloud information to a file.

    The current outputs include:
    - total current number of parcels
    - total current mass of parcels
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        clouds (str): A space-separated list of cloud names.
                      For example: 'cloud1 cloud2', 'cloud1', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "cloudInfo"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type        cloudInfo;
        libs        ("liblagrangianFunctionObjects.so");

        clouds      ({clouds});
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                  solvers                                                                      #
# --------------------------------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# scalarTransport
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_scalarTransport(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    r"""
    Evolves a passive scalar transport equation.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "scalarTransport"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            scalarTransport;
        libs            ("libsolverFunctionObjects.so");
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
#                                                                utilities                                                                      #
# --------------------------------------------------------------------------------------------------------------------------------------------- #

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# ensightWrite
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_ensightWrite(latestTime: bool = False, time: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    Writes fields in ensight format.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names.
                      For example: 'omega k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    fields = check_fields(fields)
    func = "scalarTransport"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            ensightWrite;
        libs            (utilityFunctionObjects);
        fields          ({fields});
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# solverInfo
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_solverInfo(latestTime: bool = False, time: str = "", fields: str = "", case_dir: str = "") -> str:
    r"""
    Writes solver information for a list of user-specified fields.

    Information written to file includes:
    - residual fields
    - solver type
    - initial residual
    - final residual
    - number of solver iterations
    - convergence flag
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names.
                      For example: 'omega k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    fields = check_fields(fields)
    func = "solverInfo"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            solverInfo;
        libs            ("libutilityFunctionObjects.so");
        fields          ({fields});
        writeResidualFields yes;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# writeDictionary
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_writeDictionary(latestTime: bool = False, time: str = "", dictNames: str = "", case_dir: str = "") -> str:
    r"""
    Reports dictionary contents on change.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        dictNames (str): A space-separated list of dict names.
                      For example: 'omega k', 'epsilon', etc.
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "writeDictionary"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
        type            writeDictionary;
        libs            ("libutilityFunctionObjects.so");
        dictNames          ({dictNames});
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# blendingFactor
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_blendingFactor(latestTime: bool = False, time: str = "", field: str = "", case_dir: str = "") -> str:
    r"""
    Computes blending factor as an indicator about which of the schemes is active across the domain.

    Blending factor values mean:
    \verbatim
      0   =  scheme 0
      1   =  scheme 1
      0-1 =  a blending factor between scheme 0 and scheme 1
    \endverbatim
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        field (str): Name of the operand field. Defaults to "".
                     For example: "U", etc. 
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "blendingFactor"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            blendingFactor;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entry (runtime modifiable)
    field           {field};

    // Optional entries (runtime modifiable)
    phi             phi;
    tolerance       0.001;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# columnAverage
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_columnAverage(latestTime: bool = False, time: str = "", fields: str = "", patches: str = "", case_dir: str = "") -> str:
    r"""
    Computes the arithmetic average of given quantities along columns of cells
    in a given direction for structured-like layered meshes. It is, for example,
    useful for channel-like cases where spanwise average of a field is desired.
    However, the \c columnAverage function object does not operate on arbitrary
    unstructured meshes.

    For each patch face, calculates the average value of all cells attached in
    the patch face normal direction, and then pushes the average value back
    to all cells in the column.
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        patches (str): A space-separated list of patch names. For example: 'patch1 patch2', 'patch1', etc.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    patches = check_patches(patches)
    func = "columnAverage"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            columnAverage;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    patches         ({patches});
    fields          ({fields});

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# continuityError
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_continuityError(latestTime: bool = False, time: str = "", fields: str = "", patches: str = "", case_dir: str = "") -> str:
    r"""
    Computes local, global and cumulative continuity errors for a flux field.
    
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. 
                              For example: ':100, 120, 160:200, 300:', 'none', etc. 
                              Default is an empty string, meaning this option is not used.
        case_dir (str): The case directory. Defaults to "".
    
    """
    
    func = "continuityError"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            continuityError;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    phi             phi;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    if latestTime:
        command += f" -latestTime"
    if time != "":
        command += f" -time '{time}'"

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# derivedFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_derivedFields(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    r"""
    Computes two predefined derived fields, i.e. \c rhoU, and \c pTotal, where
    the defined fields are hard-coded as follows:

    \vartable
      rhoU              | \f$ \rho \vec U \f$
      pTotal            | \f$ p + 1/2 \rho \, mag(\vec U)^2 \f$
    \endvartable
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "derivedFields"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            derivedFields;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    derived         (rhoU pTotal);

    // Optional entries (runtime modifiable)
    rhoRef          1.0;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# DESModelRegions
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_DESModelRegions(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    r"""
    Computes an indicator field for detached eddy simulation (DES) turbulence
    calculations, where the values of the indicator mean:

    \verbatim
      0 = Reynolds-averaged Navier-Stokes (RAS) regions
      1 = Large eddy simulation (LES) regions
    \endverbatim
        
    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "DESModelRegions"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            DESModelRegions;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    result          DESField;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# extractEulerianParticles
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_extractEulerianParticles(latestTime: bool = False, time: str = "", case_dir: str = "", faceZone: str = "", alpha: str = "") -> str:
    r"""
    Generates particle size information from Eulerian calculations, e.g. \c VoF.
    
    Args:
        faceZone (str): Name of faceZone used as collection surface.
        alpha (str): Name of phase indicator field.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "extractEulerianParticles"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            extractEulerianParticles;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    faceZone        {faceZone};
    alpha           {alpha};

    // Optional entries (runtime modifiable)
    alphaThreshold  0.1;
    nLocations      0;
    U               U;
    rho             rho;
    phi             phi;
    minDiameter     1e-30;
    maxDiameter     1e30;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# fieldExtents
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_fieldExtents(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", threshold: float = 0.5) -> str:
    r"""
    Computes the spatial minimum and maximum extents of an input field.

    The extents are derived from the bound box limits after identifying the
    locations where field values exceed the user-supplied threshold value.
    
    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        threshold (float): Value to identify extents boundary.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "fieldExtents"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            fieldExtents;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields              ({fields});
    threshold           {threshold};

    // Optional entries (runtime modifiable)
    internalField       true;
    referencePosition   (0 0 0);

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# flux
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_flux(latestTime: bool = False, time: str = "", case_dir: str = "", field: str = "") -> str:
    r"""
    Computes the flux of an input vector field.
    
    Args:
        field (str, optional): Name of the operand field. Defaults to ''. For example: 'U', etc.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "flux"
    func_id = get_func_id(func, case_dir)

    field_line = f"field           {field};\n" if field != "" else ""
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            flux;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    rho             none;

    // Optional (inherited) entries
    {field_line}
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# fluxSummary
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_fluxSummary(latestTime: bool = False, time: str = "", case_dir: str = "", mode: str = "") -> str:
    r"""
    Computes the volumetric- or mass-flux
    information across selections of face zones.
    
    Args:
        mode (str): Mode to generate faces to test. Options are:
                    * faceZone
                    * surface
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "fluxSummary"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            fluxSummary;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    mode            {mode};

    // Optional entries  (runtime modifiable)
    phi             phi;
    scaleFactor     1.0;
    tolerance       0.8;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# heatTransferCoeff
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_heatTransferCoeff(latestTime: bool = False, time: str = "", case_dir: str = "", field: str = "", patches: str = "", htcModel: str = "", UInf: str = "(20 0 0)", rho: float = 1.2) -> str:
    r"""
    Computes the heat transfer coefficient [W/(m^2 K)]
    as a \c volScalarField for a given set of patches.

    The heat transfer coefficient is definition dependent;
    therefore, different coefficient values could be
    obtained based on different definitions.

    
    Args:
        field (str): Name of the operand field. Defaults to ''. For example: 'U', etc.
        patches (str): A space-separated list of patch names. For example: 'patch1 patch2', 'patch1', etc.
        htcModel (str): Model for calculating heat transfer coefficient. Options are:
                        * ReynoldsAnalogy: Reynolds analogy
                        * localReferenceTemperature: local reference temperature
                        * fixedReferenceTemperature: fixed reference temperature
        UInf (str): Reference flow speed. It is a vector of three components.
                    Example: (1 0 0), (0 1 0), etc.
        rho (float): Fluid density.
                   Example: 1.2, 1.3, etc.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "heatTransferCoeff"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            heatTransferCoeff;
    libs            (fieldFunctionObjects);
    field           {field};
    patches         ({patches});
    htcModel        {htcModel};
    UInf            {UInf};
    Cp              1000;
    rho             {rho};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# interfaceHeight
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_interfaceHeight(latestTime: bool = False, time: str = "", case_dir: str = "", locations: str = "", alpha: str = "alpha.water", liquid: str = "true", direction: str = "(1 0 0)") -> str:
    r"""
    This function object reports the height of the interface above a set of
    locations.

    For each location, it writes the vertical distance of the
    interface above both the location and the lowest boundary. It also writes
    the point on the interface from which these heights are computed. It uses
    an integral approach, so if there are multiple interfaces above or below a
    location then this method will generate average values.

    Args:
        locations (str): Locations to report the height at.
                        Example: '(0 0 0) (10 0 0) (20 0 0)', '(0 0 0)', etc.
        alpha (str, optional): 	Name of alpha field.
        liquid (str, optional): Flag if the alpha field that of the liquid.
        direction (str, optional): Direction of the interface.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "interfaceHeight"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            interfaceHeight;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    locations       ({locations});

    // Optional entries (runtime modifiable)
    alpha           {alpha};
    liquid          {liquid};
    direction       {direction};
    interpolationScheme    cellPoint;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# limitFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_limitFields(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", limit: str = "max", value: float = 100) -> str:
    r"""
    Limits input fields to user-specified min and max bounds.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        limit (str): Bound to limit. Options are:
                     * min
                     * max
        value (float): limit value.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "limitFields"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            limitFields;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields          ({fields});
    model           equalBinWidth;
    limit           {limit};
    {limit}         {value};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# mapFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_mapFields(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", mapRegion: str = "", mapMethod: str = "direct", consistent: str = "true") -> str:
    r"""
    Maps input fields from local mesh to secondary mesh at runtime.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        mapRegion (str): Name of region to map to.
        mapMethod (str): Mapping method. Options are:
                         * direct
                         * mapNearest
                         * cellVolumeWeight
                         * correctedCellVolumeWeight
        consistent (str): Flag to use consistent mapping.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "mapFields"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            mapFields;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entries (runtime modifiable)
    fields          ({fields});
    mapRegion       {mapRegion};
    mapMethod       {mapMethod};
    consistent      {consistent};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# momentum
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_momentum(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    r"""
    Computes linear/angular momentum, reporting integral values and optionally writing the fields.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "momentum"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            momentum;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    regionType      all;
    writeMomentum   yes;
    writePosition   yes;
    writeVelocity   yes;
    p               p;
    U               U;
    rho             rho;
    rhoRef          1.0;

    cylindrical     false;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# momentumError
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_momentumError(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", mapRegion: str = "", mapMethod: str = "direct", consistent: str = "true") -> str:
    r"""
    Computes balance terms for the steady momentum equation.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "momentumError"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            momentumError;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    p               p;
    U               U;
    phi             phi;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# nearWallFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_nearWallFields(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "", patches: str = "", distance: float = 0.01) -> str:
    r"""
    Samples near-patch volume fields within an input distance range.

    Args:
        patches (str): A space-separated list of patch names. For example: 'patch1 patch2', 'patch1', etc.
        fields (str): Names of input-output fields.
                    Example: "(field1 outField1)\n(field2 outField2)".
        distance (float): Wall-normal distance from patch to sample. 
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "nearWallFields"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            nearWallFields;
    libs            (fieldFunctionObjects);
    fields
    (
        {fields}
    );
    patches         ({patches});
    distance        {distance};

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# particleDistribution
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_particleDistribution(latestTime: bool = False, time: str = "", case_dir: str = "", cloud: str = "", nameVsBinWidth: str = "") -> str:
    r"""
    Generates a particle distribution for lagrangian data at a given time.

    Args:
        cloud (str): Name of cloud to process.  
        nameVsBinWidth (str): List of cloud field-bin width. 
                            Example: "(d 0.1)\n(U 10)".
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "particleDistribution"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type        particleDistribution;
    libs        (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    cloud       {cloud};
    nameVsBinWidth
    (
        {nameVsBinWidth}
    );
    setFormat   raw;

    // Optional entries (runtime modifiable)
    tagField    none;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# pressure
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_pressure(latestTime: bool = False, time: str = "", case_dir: str = "", mode: str = "") -> str:
    r"""
    Provides several methods to convert an input pressure field into derived forms.

    Args:
        mode (str): Calculation mode. Options:
                    static      | static pressure
                    total       | total pressure
                    isentropic  | isentropic pressure
                    staticCoeff | static pressure coefficient
                    totalCoeff  | total pressure coefficient
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "pressure"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries
    type            pressure;
    libs            (fieldFunctionObjects);
    mode            {mode};

    // Optional entries
    U               U;
    rho             rhoInf;
    rhoInf          1.0;
    pRef            1.0;
    pInf            1.0;
    UInf            (1 0 0);

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0.25;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 15;
    writeControl    timeStep;
    writeInterval   75;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# proudmanAcousticPower
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_proudmanAcousticPower(latestTime: bool = False, time: str = "", case_dir: str = "", alphaEps: float = 0.1, rhoInf: float = None, aRef: float = None) -> str:
    r"""
    Computes the acoustic power due to the volume of isotropic turbulence using Proudman's formula.

    Args:
        alphaEps (float, optional): Empirical model coefficient. Defaults to 0.1.
        rhoInf (float, optional): For incompressible flow simulations. Reference Freestream density.
        aRef (float, optional): For incompressible flow simulations. Reference Speed of sound.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "proudmanAcousticPower"
    func_id = get_func_id(func, case_dir)

    add_rhoInf_aRef_options = ''
    if rhoInf != None and aRef != None:
        add_rhoInf_aRef_options = f'''
        rhoInf      {rhoInf};
        aRef        {aRef};
        '''
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            proudmanAcousticPower;
    libs            (fieldFunctionObjects);

    // Optional entries (runtime modifiable)
    alphaEps    {alphaEps};
    {add_rhoInf_aRef_options}

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# reactionsSensitivityAnalysis
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_reactionsSensitivityAnalysis(latestTime: bool = False, time: str = "", case_dir: str = "") -> str:
    r"""
    Computes indicators for reaction rates of creation or destruction
    of species in each reaction.

    Args:
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "reactionsSensitivityAnalysis"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            reactionsSensitivityAnalysis;
    libs            (fieldFunctionObjects);

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# readFields
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_readFields(latestTime: bool = False, time: str = "", case_dir: str = "", fields: str = "") -> str:
    r"""
    Reads fields from the time directories and adds them to the mesh database for further post-processing.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "readFields"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            readFields;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields      ({fields});

    // Optional entries (runtime modifiable)
    readOnStart true;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# reference
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_reference(latestTime: bool = False, time: str = "", case_dir: str = "", field: str = "") -> str:
    r"""
    Computes a field whose values are offset to a reference value obtained by from a Function1.

    Args:
        field (str): Name of the operand field. Defaults to ''. For example: 'U', etc.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "reference"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            reference;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entries (runtime modifiable)
    field           {field};

    // Optional entries (runtime modifiable)
    refValue        sample;
    position    (0 0 0);
    scale       1.0;
    offset      (0.0 0.0 0.0);
    interpolationScheme    cell;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



# --------------------------------------------------------------------------------------------------------------------------------------------- #
# setFlow
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_setFlow(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    mode: str = "", 
    velocity: str = "(1 0 0)", 
    omega: str = "6.28", 
    origin: str = "(0.5 0 0.5)",
    refDir: str = "(1 0 0)",
    axis: str = "(0 1 0)"
    ) -> str:
    r"""
    Provides options to set the velocity and flux fields as a function of time.

    Useful for testing advection behaviour of numerical schemes by e.g.
    imposing solid body rotation, vortex flows.  All types include a scaling
    \c Function1 type enabling the strength of the transformation to vary
    as a function of time.

    Args:
        mode(str): Operating mode. Options are:
                function
                rotation
                vortex2D
                vortex3D
        velocity(str, optional): Velocity function.
        omega(str, optional): Rotational speed function.
        origin(str, optional): Rotation vector origin.
        refDir(str, optional): Rotation vector reference direction.
        axis(str, optional): Rotation vector axis.

        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "setFlow"
    func_id = get_func_id(func, case_dir)

    if mode == "function":
        mode_entries = f'''
        velocity    {velocity};
        '''
    elif mode == "rotation":
        mode_entries = f'''
        omega   {omega};
        origin  {origin};
        refDir  {refDir};
        axis    {axis};
        '''
    elif mode == "vortex2D" or mode == "vortex3D":
        mode_entries = f'''
        origin  {origin};
        refDir  {refDir};
        axis    {axis};
        '''
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            setFlow;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    mode        {mode};
    scale       1;

    // Optional entries (runtime modifiable)
    U           U;
    rho         none;
    phi         phi;
    reverseTime 1;

    {mode_entries}

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# stabilityBlendingFactor
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_stabilityBlendingFactor(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    field: str = "", 
    result: str = "UBlendingFactor"
    ) -> str:
    r"""
    Computes the \c stabilityBlendingFactor to be used by the
    local blended convection scheme. The output is a surface field weight
    between 0-1.

    Args:
        field (str): Name of the operand field. Defaults to ''. For example: 'U', etc.
        result(str): Name of surface field used in the localBlended scheme.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    func = "stabilityBlendingFactor"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type                 stabilityBlendingFactor;
    libs                 (fieldFunctionObjects);

    // Mandatory entries (unmodifiable)
    field               {field};
    result              {result};

    // Optional entries (runtime modifiable)
    tolerance           0.001;

    // Any of the options can be chosen in combinations

    // Option-1
    switchNonOrtho      true;
    nonOrthogonality    nonOrthoAngle;
    maxNonOrthogonality 20;
    minNonOrthogonality 60;

    // Option-2
    switchGradCc        true;
    maxGradCc           3;
    minGradCc           4;

    // Option-3
    switchResiduals     true;
    maxResidual         10;
    residual            initialResidual:p;
    P                   1.5;
    I                   0;
    D                   0.5;

    // Option-4
    switchFaceWeight    true;
    maxFaceWeight       0.3;
    minFaceWeight       0.2;

    // Option-5
    switchSkewness      true;
    maxSkewness         2;
    minSkewness         3;

    // Option-6
    switchCo            true;
    U                   U;
    Co1                 1;
    Co2                 10;

    // Optional (inherited) entries
    writePrecision      8;
    writeToFile         true;
    useUserTime         true;
    region              region0;
    enabled             true;
    log                 true;
    timeStart           0;
    timeEnd             1000;
    executeControl      timeStep;
    executeInterval     1;
    writeControl        timeStep;
    writeInterval       1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaceInterpolate
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaceInterpolate(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    fields: str = ""
    ) -> str:
    r"""
    Linearly interpolates volume fields to generate surface fields.

    Args:
        fields(str): List of input and output fields.
                    Example: "(U surfaceU) (p surfaceP) (k surfaceK) (divU surfaceDivU)"
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "surfaceInterpolate"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            surfaceInterpolate;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields      ({fields});

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# valueAverage
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_valueAverage(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    fields: str = "",
    fo: str = ""
    ) -> str:
    r"""
    Computes the ensemble- or time-based singular-value average values,
    with optional windowing, from the output of function objects
    that generate non-field type values (e.g. \c Cd of \c forceCoeffs or
    \c momentum_x in \c momentum function objects).

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        fo(str): Name of function object to retrieve data.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    fields = check_fields(fields)
    func = "valueAverage"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type              valueAverage;
    libs              (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    functionObject    {fo};
    fields            ({fields});
    windowType      exact;
    
    // Optional entries (runtime modifiable)
    resetOnRestart    false;
    window            0.5;

    // Optional (inherited) entries
    writePrecision    8;
    writeToFile       true;
    useUserTime       true;
    region            region0;
    enabled           true;
    log               true;
    timeStart         0;
    timeEnd           1000;
    executeControl    timeStep;
    executeInterval   1;
    writeControl      timeStep;
    writeInterval     1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# zeroGradient
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_zeroGradient(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    fields: str = "",
    ) -> str:
    r"""
    Creates a volume field with zero-gradient boundary conditions from another volume field.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """
    
    fields = check_fields(fields)
    
    func = "zeroGradient"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            zeroGradient;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    fields          ({fields});

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# histogram
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_histogram(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    field: str = "",
    nBins: int = 100,
    ) -> str:
    r"""
    Computes the volume-weighted histogram of an input volScalarField.

    Args:
        nBins (int): Number of bins.
        field (str): Name of field.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """

    func = "histogram"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            histogram;
    libs            (fieldFunctionObjects);

    // Mandatory (inherited) entries (runtime modifiable)
    field       {field};
    nBins       {nBins};
    setFormat   gnuplot;

    // Optional entries (runtime modifiable)
    max         5;
    min        -5;

    // Optional (inherited) entries
    writePrecision  8;
    writeToFile     true;
    useUserTime     true;
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# forceCoeffs
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_forceCoeffs(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    patches: str = "",
    rhoInf: float = 1.225,
    CofR: str = "(0 0 0)",
    liftDir: str = "(0 1 0)",
    dragDir: str = "(1 0 0)",
    pitchAxis: str = "(0 0 1)",
    magUInf: float = 1,
    lRef: float = 1,
    Aref: float = 1,
    ) -> str:
    r"""
    Computes force and moment coefficients over a given
    list of patches, and optionally over given porous zones.

    Args:
        patches (str): A space-separated list of patch names to sample. ',' is not allowed. For example: 'patch1 patch2 patch3'.
        rhoInf (float): Density of the fluid.
        CofR (str): Center of rotation.
        liftDir (str): Lift direction.
        dragDir (str): Drag direction.
        pitchAxis (str): Pitch axis.
        magUInf (float): Magnitude of the free-stream velocity.
        lRef (float): Length of the wing.
        Aref (float): Area of the wing.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """

    func = "forceCoeffs"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
        type            forceCoeffs;
        libs            (forces);
        writeControl    writeTime;

        patches     ({patches});

        rho         rhoInf;
        rhoInf      {rhoInf};

        CofR        {CofR};
        liftDir     {liftDir};
        dragDir     {dragDir};
        pitchAxis   {pitchAxis};
        magUInf     {magUInf};
        lRef        {lRef};
        Aref        {Aref};
    }}
    '''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# forces
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_forces(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    patches: str = "",
    rhoInf: float = 1,
    CofR: str = "(0 0 0)",
    pitchAxis: str = "(0 1 0)",
    ) -> str:
    r"""
    Computes forces and moments over a given list of patches by integrating
    pressure and viscous forces and moments, and optionally resistance forces
    and moments from porous zones.

    Args:
        patches (str): A space-separated list of patch names to sample. ',' is not allowed. For example: 'patch1 patch2 patch3'.
        rhoInf (float): Density of the fluid.
        CofR (str): Center of rotation.
        pitchAxis (str): Pitch axis.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """

    func = "forces"
    func_id = get_func_id(func, case_dir)
    
    function_content = f'''
    {func_id}
    {{
        type          forces;
        libs          (forces);

        writeControl  timeStep;
        timeInterval  1;

        patches       ({patches});
        rho           rhoInf;
        log           true;
        rhoInf        {rhoInf};

        CofR          {CofR};
        pitchAxis     {pitchAxis};
    }}
    '''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# fieldAverage
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_fieldAverage(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    fields: str = "",
    ) -> str:
    r"""
    Computes ensemble- and/or time-based field averages, with optional
    windowing, for a user-specified selection of volumetric and/or surface
    fields.
    Fields are entered as a list of sub-dictionaries, which indicate the type of
    averages to perform, and can be updated during the calculation.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    
    """

    func = "fieldAverage"
    func_id = get_func_id(func, case_dir)
    
    fields_list = fields.split(" ")
    fields_content = ""
    for field in fields_list:
        fields_content += f'''
        {field}
        {{
            mean        on;
            prime2Mean  on;
            base        time;
        }}
        '''

    function_content = f'''
    {func_id}
    {{
        type            fieldAverage;
        libs            (fieldFunctionObjects);
        writeControl    writeTime;

        fields
        (
            {fields_content}
        );

    }}
    '''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# streamLine
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_streamLine(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    fields: str = "",
    setFormat: str = "vtk",
    direction: str = "bidirectional",
    axis: str = "",
    start: str = "",
    end: str = "",
    nPoints: int = 2000,
    ) -> str:
    r"""
    Generates streamline data by sampling a set of user-specified fields along a
    particle track, transported by a user-specified velocity field.

    Args:
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'. 
        setFormat (str): Set format. Defaults to vtk. Options are: csv, ensight, gnuplot, jplot, nastran, raw, vtk, xmgr.
        direction (str): Direction. Defaults to bidirectional. Options are: bidirectional, forward, backward.
        axis (str): Axis. Options are: x, y, z.
        start (str): Start point, separate x, y, and z coordinates with spaces. For example: '(0 0 0)'.
        end (str): End point, separate x, y, and z coordinates with spaces.. For example: '(0 0 0)'.
        nPoints (int): Number of points. Default is 200.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    """

    func = "streamLine"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries
    type            streamLine;
    libs            (fieldFunctionObjects);
    U               U;
    fields          ({fields});
    setFormat       {setFormat};
    direction       {direction};
    lifeTime        10000;
    cloud           particleTracks;
    maxTrackLength  1000;
    seedSampleSet
    {{
        type        uniform;
        axis        {axis};
        start       {start};
        end         {end};
        nPoints     {nPoints};
    }}

    nSubCycle       5;
    interpolationScheme cellPoint;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         10000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    writeTime;
    writeInterval   -1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command

# --------------------------------------------------------------------------------------------------------------------------------------------- #
# surfaceDistance
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_surfaceDistance(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    obj_name: str = "",
    surface_type: str = "",
    surface_name: str = "",
    ) -> str:
    r"""
    Computes the distance to the nearest surface from a given geometry.

    Args:
        obj_name (str): Name of the object. For example: 'motorBike.obj'. 
        surface_type (str): Surface type.
        surface_name (str): Surface name.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    """

    func = "surfaceDistance"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries
    type            surfaceDistance;
    libs            (fieldFunctionObjects);
    geometry
    {{
        {obj_name}
        {{
            type {surface_type};
            name {surface_name};
        }}
    }}

    // Optional entries
    calculateCells  true;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  writeTime;
    executeInterval -1;
    writeControl    writeTime;
    writeInterval   -1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# externalCoupled
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_externalCoupled(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    regionName: str = "",
    writeFields: str = "",
    readFields: str = "",
    ) -> str:
    r"""
    Provides a simple file-based communication interface for explicit coupling
    with an external application, so that data is transferred to- and from
    OpenFOAM. The data exchange employs specialised boundary conditions to
    provide either one-way or two-way coupling models.

    Args:
        writeFields (str): Fields to output in commsDir. A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'. 
        readFields (str): Fields to read from commsDir. A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'. 
        regionName (str): The regions to couple.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    """

    func = "surfaceDistance"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            externalCoupled;
    libs            (fieldFunctionObjects);
    // Directory to use for data exchange
    commsDir        "${{FOAM_CASE}}/comms";
    regions
    {{
        {regionName}
        {{
            coupleGroup
            {{
                writeFields ({writeFields});

                readFields  ({readFields});
            }}
        }}
    }}
    initByExternal  true;

    // Optional entries (runtime modifiable)
    waitInterval    1;
    timeOut         100;
    statusDone      done;
    calcFrequency   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command


# --------------------------------------------------------------------------------------------------------------------------------------------- #
# wallBoundedStreamLine
# --------------------------------------------------------------------------------------------------------------------------------------------- #
@app.tool()
def postProcess_wallBoundedStreamLine(
    latestTime: bool = False, 
    time: str = "", 
    case_dir: str = "", 
    tracking_U: str = "",
    fields: str = "",
    setFormat: str = "",
    direction: str = "",
    axis: str = "",
    start: str = "",
    end: str = "",
    nPoints: int = 10,
    ) -> str:
    r"""
    Generates streamline data by sampling a set of user-specified fields along a
    particle track, transported by a user-specified velocity field, constrained
    to a patch.

    Args:
        tracking_U (str): Name of tracking velocity field. For example: 'U'.
        fields (str): A space-separated list of field names to sample. ',' is not allowed. For example: 'omega k'. 
        setFormat (str): Set format. Options are: csv, ensight, gnuplot, jplot, nastran, raw, vtk, xmgr.
        direction (str): Direction. Options are: bidirectional, forward, backward.
        axis (str): Axis. Options are: x, y, z.
        start (str): Start point. For example: '(0 0 0)'.
        end (str): End point. For example: '(0 0 0)'.
        nPoints (int): Number of points. Default is 10.
        latestTime (bool, optional): Whether to calculate only the last time step. Defaults to False.
        time (str, optional): Specifies the range of time steps to process. For example: ':100, 120, 160:200, 300:', 'none', etc. Default is an empty string, meaning this option is not used.
        case_dir (str, optional): The case directory. Defaults to '.'.
    """

    func = "wallBoundedStreamLine"
    func_id = get_func_id(func, case_dir)

    function_content = f'''
    {func_id}
    {{
    // Mandatory entries (unmodifiable)
    type            wallBoundedStreamLine;
    libs            (fieldFunctionObjects);

    // Mandatory entries (runtime modifiable)
    U               {tracking_U};
    fields          ({fields});
    setFormat       {setFormat};
    direction       {direction};
    lifeTime        10000;
    cloud           particleTracks;
    seedSampleSet
    {{
        type        uniform;
        axis        {axis};
        start       {start};
        end         {end};
        nPoints     {nPoints};
    }}

    // Optional entries (runtime modifiable)
    bounds          (0.2 -10 -10)(0.22 10 10);
    trackLength     1e-3;
    nSubCycle       1;
    interpolationScheme cellPoint;

    // Optional (inherited) entries
    region          region0;
    enabled         true;
    log             true;
    timeStart       0;
    timeEnd         1000;
    executeControl  timeStep;
    executeInterval 1;
    writeControl    timeStep;
    writeInterval   1;
    }}
'''

    # 写入 system/postProcessingDict 文件
    write_function_objects(case_dir, function_content)

    # 获取求解器名称
    solver = get_solver_name(case_dir)

    command = f"{solver} -postProcess -dict system/postProcessingDict"
    
    command = add_latest_time_option(command, latestTime)
    command = add_time_option(command, time)

    return command



if __name__ == "__main__":
    app.run(transport='stdio')
