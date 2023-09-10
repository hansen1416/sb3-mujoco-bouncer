import math
import time

import numpy as np
import mujoco
import mujoco.viewer
from transforms3d import quaternions


tall = 1.6

left_shouder = -0.4
right_shouder = 0.4

target_x = -1.1
target_y = 0.52
target_z = 1.4

upper_arm_l = 0.4
lower_arm_l = 0.4
hand_l = 0.14

skin_color = '0.8 0.6 0.4 1'

string_length = 0.4
anchor_z = target_z + string_length

xml = """
<mujoco>
    <asset>
        <texture name="grid" type="2d" builtin="checker" rgb1=".1 .2 .3"
        rgb2=".2 .3 .4" width="300" height="300"/>
        <material name="grid" texture="grid" texrepeat="8 8" reflectance=".2"/>
    </asset>
    <worldbody>
        
        <light pos="0 0 2."/>
        
        <geom size="1 1 .01" type="plane" material="grid"/>
        
        <site name="anchor" pos="{target_x} {target_y} {anchor_z}" size=".01"/>

        <body pos="0 0 0">
            <geom name="spine" type="box" fromto="0 0 0. 0 0 {tall}" size=".1" 
                pos="0 0 0" rgba="1 1 1 1"/>
            <geom name="shoulder" type="box" fromto="0 {left_shouder} {tall} 0 {right_shouder} {tall}" size=".1" 
                pos="0 0 0" rgba="1 1 1 1"/>

            <!-- Shoulder joint -->
            <body pos="0. 0.55 {tall}" gravcomp="1">
                <joint name="shoulder" type="ball" pos="0 0 0"/>
                <geom name="upper_arm" type="cylinder" fromto="0 0. 0. 0 0. -{upper_arm_l}" size="0.1" 
                rgba="{skin_color}"/>

                <!-- Elbow joint -->
                <body pos="0. 0. -0.6" gravcomp="1">
                    <joint name="elbow" type="hinge" pos="0 0 0.1" axis="0 1 0"/>
                    <geom name="lower_arm" type="cylinder"  fromto="0 0 0. 0 0 -{lower_arm_l}" size=".08" 
                    pos="0 0 0" rgba="{skin_color}"/>

                    <!-- Wrist joint -->
                    <body pos="0. 0. -{lower_arm_l}" gravcomp="1">
                        <geom name="hand" type="cylinder" fromto="0 0 0.0 0 0 -{hand_l}" size="0.09" 
                        pos="0 0 0" rgba="{skin_color}"/>
                    </body>
                </body>
            </body>
        </body>

        <body name="target" pos="{target_x} {target_y} {target_z}">
            <joint name="free" type="free"/>
            <geom name="red_sphere" type="sphere" size=".06" rgba="1 0 0 1"/>
            <site name="hook" pos="0. 0. 0." size=".01"/>
        </body>

    </worldbody>

    <tendon>
        <spatial name="wire" limited="true" range="0 {string_length}" width="0.003">
        <site site="anchor"/>
        <site site="hook"/>
        </spatial>
    </tendon>
</mujoco>
""".format(tall=tall, left_shouder=left_shouder, right_shouder=right_shouder,
           upper_arm_l=upper_arm_l, lower_arm_l=lower_arm_l, hand_l=hand_l, skin_color=skin_color,
           target_x=target_x, target_y=target_y, target_z=target_z,
           anchor_z=anchor_z, string_length=string_length)


class ArmSim:

    def __init__(self, xml) -> None:
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        # enable joint visualization option:
        scene_option = mujoco.MjvOption()
        scene_option.flags[mujoco.mjtVisFlag.mjVIS_JOINT] = True

        self.model.opt.timestep = 0.002

    def run(self):
        # todo this is linear speed, add acceleration
        shoulder_angle = np.linspace(10, 86, 100)
        elbow_angle = np.linspace(110, 0, 100)
        motion_idx = 0
        direction = 1

        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)

        with mujoco.viewer.launch_passive(self.model, self.data) as viewer:

            # set camera
            viewer.cam.lookat[0] = 0  # x position
            viewer.cam.lookat[1] = 0  # y position
            viewer.cam.lookat[2] = 0  # z position
            viewer.cam.distance = 5  # distance from the target
            viewer.cam.elevation = -30  # elevation angle
            viewer.cam.azimuth = 0  # azimuth angle

            # random initial rotational velocity:
            mujoco.mj_resetData(self.model, self.data)

            print(self.data.qpos)
            print(self.data.qvel)

            # Close the viewer automatically after 30 wall-seconds.
            start = time.time()

            while viewer.is_running() and time.time() - start < 5:

                step_start = time.time()

                mujoco.mj_step(self.model, self.data)

                # joint manipulation start

                q = quaternions.axangle2quat(
                    [0, 1, 0], math.radians(shoulder_angle[motion_idx]), is_normalized=True)

                self.data.qpos[0] = q[0]  # w
                self.data.qpos[1] = q[1]  # x
                self.data.qpos[2] = q[2]  # y
                self.data.qpos[3] = q[3]  # z

                self.data.qpos[4] = math.radians(elbow_angle[motion_idx])  # w
                self.data.qvel[3] = 0
                # print(data.qvel)

                if direction == 1:
                    motion_idx += 1
                else:
                    motion_idx -= 1

                if motion_idx >= len(elbow_angle) - 1:
                    direction *= -1
                elif motion_idx <= 0:
                    direction *= -1

                # joint manipulation end

                # Pick up changes to the physics state, apply perturbations, update options from GUI.
                viewer.sync()

                # Rudimentary time keeping, will drift relative to wall clock.
                time_until_next_step = self.model.opt.timestep - \
                    (time.time() - step_start)

                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)


if __name__ == "__main__":
    rnder = ArmSim(xml)

    rnder.run()
