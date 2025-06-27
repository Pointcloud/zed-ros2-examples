# Copyright 2024 Stereolabs
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    IncludeLaunchDescription,
    LogInfo
)
from launch.substitutions import (
    LaunchConfiguration,
    TextSubstitution
)
from launch_ros.actions import (
    ComposableNodeContainer,
    LoadComposableNodes
)

from launch_ros.descriptions import (
    ComposableNode
)
# Enable colored output
os.environ["RCUTILS_COLORIZED_OUTPUT"] = "1"


def launch_setup(context, *args, **kwargs):

    # List of actions to be launched
    actions = []

    namespace_val = 'zed_isaac'
    disable_tf = LaunchConfiguration('disable_tf')
    camera_model = LaunchConfiguration('camera_model')

    disable_tf_val = disable_tf.perform(context)
    
    # ROS 2 Component Container
    container_name = 'zed_container'
    info = '* Starting Composable node container: /' + namespace_val + '/' + container_name
    actions.append(LogInfo(msg=TextSubstitution(text=info)))

    # Note: It is crucial that the 'executable' field is set to be 'component_container_mt'
    #  so that the created nodes can be started and communicated correctly within the same process.

    zed_container = ComposableNodeContainer(
        name=container_name,
        namespace=namespace_val,
        package='rclcpp_components',
        executable='component_container_mt',
        arguments=['--ros-args', '--log-level', 'info'],
        output='screen',
    )
    actions.append(zed_container)

   
    # ZED Wrapper launch file
    zed_wrapper_launch = IncludeLaunchDescription(
        launch_description_source=PythonLaunchDescriptionSource([
            get_package_share_directory('zed_wrapper'),
            '/launch/zed_camera.launch.py'
        ]),
        launch_arguments={
            'camera_model': camera_model,
            'container_name': container_name,
            'namespace': namespace_val,
            'enable_ipc': 'false'
        }.items()
    )
    actions.append(zed_wrapper_launch)

    # AprilTag detection node
    apriltag_node = ComposableNode(
        package='isaac_ros_apriltag',
        plugin='nvidia::isaac_ros::apriltag::AprilTagNode',
        name='apriltag',
        namespace=namespace_val,
        remappings=[
                ('image', 'zed/rgb/camera_info'),
                ('camera_info', 'zed/rgb/image_rect_color')
        ],
        parameters=[{'size': 0.22,
                        'max_tags': 64,
                        'tile_size': 4}
        ]
    )

    # Add the AprilTag node to the container
    load_april_tag_node = LoadComposableNodes(
        composable_node_descriptions=[apriltag_node],
        target_container=('/' + namespace_val + '/' + container_name)
    )
    actions.append(load_april_tag_node)
    return actions

def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'camera_model',
                description='[REQUIRED] The model of the camera. Using a wrong camera model can disable camera features.',
                choices=['zed', 'zedm', 'zed2', 'zed2i', 'zedx', 'zedxm', 'virtual', 'zedxonegs', 'zedxone4k']),
            DeclareLaunchArgument(
                'disable_tf',
                default_value='False',
                description='If `True` disable TF broadcasting for all the cameras in order to fuse visual odometry information externally.'),
            OpaqueFunction(function=launch_setup)
        ]
    )
