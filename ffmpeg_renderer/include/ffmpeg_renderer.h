// https://github.com/tsoding/rendering-video-in-c-with-ffmpeg

#ifndef FFMPEG_H_
#define FFMPEG_H_

#include <stddef.h>

typedef struct FFMPEG FFMPEG;

FFMPEG *ffmpeg_start_rendering(size_t width, size_t height, size_t fps);
// TODO: handle potential error that may happen in all of the ffmpeg function
void ffmpeg_send_frame(FFMPEG *ffmpeg, void *data, size_t width, size_t height);
// TODO: use -vflip of ffmpeg instead
void ffmpeg_send_frame_flipped(FFMPEG *ffmpeg, void *data, size_t width, size_t height);
void ffmpeg_end_rendering(FFMPEG *ffmpeg);

#endif // FFMPEG_H_

#ifdef FFMPEG_IMPLEMENTATION

#if defined(__unix__)
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>

#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define READ_END 0
#define WRITE_END 1

struct FFMPEG {
    int pid;
    int pipe;
};

FFMPEG *ffmpeg_start_rendering(size_t width, size_t height, size_t fps)
{
    int pipefd[2];

    if (pipe(pipefd) < 0) {
        fprintf(stderr, "ERROR: could not create a pipe: %s\n", strerror(errno));
        return NULL;
    }

    pid_t child = fork();
    if (child < 0) {
        fprintf(stderr, "ERROR: could not fork a child: %s\n", strerror(errno));
        return NULL;
    }

    if (child == 0) {
        if (dup2(pipefd[READ_END], STDIN_FILENO) < 0) {
            fprintf(stderr, "ERROR: could not reopen read end of pipe as stdin: %s\n", strerror(errno));
            exit(1);
        }
        close(pipefd[WRITE_END]);

        char resolution[64];
        snprintf(resolution, sizeof(resolution), "%zux%zu", width, height);
        char framerate[64];
        snprintf(framerate, sizeof(framerate), "%zu", fps);

        int ret = execlp("ffmpeg",
            "ffmpeg",
            "-loglevel", "verbose",
            "-y",

            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", resolution,
            "-r", framerate,
            "-i", "-",

            "-c:v", "libx264",
            "-vb", "2500k",
            "-c:a", "aac",
            "-ab", "200k",
            "-pix_fmt", "yuv420p",
            "output.mp4",

            NULL
        );
        if (ret < 0) {
            fprintf(stderr, "ERROR: could not run ffmpeg as a child process: %s\n", strerror(errno));
            exit(1);
        }
        assert(0 && "unreachable");
    }

    close(pipefd[READ_END]);

    FFMPEG *ffmpeg = malloc(sizeof(FFMPEG));
    assert(ffmpeg != NULL && "Buy MORE RAM lol!!");
    ffmpeg->pid = child;
    ffmpeg->pipe = pipefd[WRITE_END];
    return ffmpeg;
}

void ffmpeg_end_rendering(FFMPEG *ffmpeg)
{
    close(ffmpeg->pipe);
    waitpid(ffmpeg->pid, NULL, 0);
}

void ffmpeg_send_frame(FFMPEG *ffmpeg, void *data, size_t width, size_t height)
{
    write(ffmpeg->pipe, data, sizeof(uint32_t)*width*height);
}

void ffmpeg_send_frame_flipped(FFMPEG *ffmpeg, void *data, size_t width, size_t height)
{
    for (size_t y = height; y > 0; --y) {
        write(ffmpeg->pipe, (uint32_t*)data + (y - 1)*width, sizeof(uint32_t)*width);
    }
}
#elif defined(_WIN32)
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

struct FFMPEG {
    HANDLE hProcess;
    // HANDLE hPipeRead;
    HANDLE hPipeWrite;
};

static LPSTR GetLastErrorAsString(void)
{
    // https://stackoverflow.com/questions/1387064/how-to-get-the-error-message-from-the-error-code-returned-by-getlasterror

    DWORD errorMessageId = GetLastError();
    assert(errorMessageId != 0);

    LPSTR messageBuffer = NULL;

    DWORD size =
        FormatMessage(
            FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, // DWORD   dwFlags,
            NULL, // LPCVOID lpSource,
            errorMessageId, // DWORD   dwMessageId,
            MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT), // DWORD   dwLanguageId,
            (LPSTR) &messageBuffer, // LPTSTR  lpBuffer,
            0, // DWORD   nSize,
            NULL // va_list *Arguments
        );

    return messageBuffer;
}

FFMPEG *ffmpeg_start_rendering(size_t width, size_t height, size_t fps)
{
    HANDLE pipe_read;
    HANDLE pipe_write;

    SECURITY_ATTRIBUTES saAttr = {0};
    saAttr.nLength = sizeof(SECURITY_ATTRIBUTES);
    saAttr.bInheritHandle = TRUE;

    if (!CreatePipe(&pipe_read, &pipe_write, &saAttr, 0)) {
        fprintf(stderr, "ERROR: Could not create pipe: %s\n", GetLastErrorAsString());
        return NULL;
    }

    if (!SetHandleInformation(pipe_write, HANDLE_FLAG_INHERIT, 0)) {
        fprintf(stderr, "ERROR: Could not SetHandleInformation: %s\n", GetLastErrorAsString());
        return NULL;
    }

    // https://docs.microsoft.com/en-us/windows/win32/procthread/creating-a-child-process-with-redirected-input-and-output

    STARTUPINFO siStartInfo;
    ZeroMemory(&siStartInfo, sizeof(siStartInfo));
    siStartInfo.cb = sizeof(STARTUPINFO);
    // NOTE: theoretically setting NULL to std handles should not be a problem
    // https://docs.microsoft.com/en-us/windows/console/getstdhandle?redirectedfrom=MSDN#attachdetach-behavior
    siStartInfo.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    // TODO(#32): check for errors in GetStdHandle
    siStartInfo.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
    siStartInfo.hStdInput = pipe_read;
    siStartInfo.dwFlags |= STARTF_USESTDHANDLES;

    PROCESS_INFORMATION piProcInfo;
    ZeroMemory(&piProcInfo, sizeof(PROCESS_INFORMATION));

    char cmd_buffer[1024*2];
    snprintf(cmd_buffer, sizeof(cmd_buffer), "ffmpeg.exe -loglevel verbose -y -f rawvideo -pix_fmt rgba -s %dx%d -r %d -i - -c:v libx264 -vb 2500k -c:a aac -ab 200k -pix_fmt yuv420p output.mp4", width, height, fps);

    BOOL bSuccess =
        CreateProcess(
            NULL,
            cmd_buffer,
            NULL,
            NULL,
            TRUE,
            0,
            NULL,
            NULL,
            &siStartInfo,
            &piProcInfo
        );

    if (!bSuccess) {
        fprintf(stderr, "ERROR: Could not create child process: %s\n", GetLastErrorAsString());
        return NULL;
    }

    CloseHandle(pipe_read);
    CloseHandle(piProcInfo.hThread);

    // TODO: use Windows specific allocation stuff?
    FFMPEG *ffmpeg = malloc(sizeof(FFMPEG));
    assert(ffmpeg != NULL && "Buy MORE RAM lol!!");
    ffmpeg->hProcess = piProcInfo.hProcess;
    // ffmpeg->hPipeRead = pipe_read;
    ffmpeg->hPipeWrite = pipe_write;
    return ffmpeg;
}

void ffmpeg_send_frame(FFMPEG *ffmpeg, void *data, size_t width, size_t height)
{
    WriteFile(ffmpeg->hPipeWrite, data, sizeof(uint32_t)*width*height, NULL, NULL);
}

void ffmpeg_send_frame_flipped(FFMPEG *ffmpeg, void *data, size_t width, size_t height)
{
    for (size_t y = height; y > 0; --y) {
        WriteFile(ffmpeg->hPipeWrite, (uint32_t*)data + (y - 1)*width, sizeof(uint32_t)*width, NULL, NULL);
    }
}

void ffmpeg_end_rendering(FFMPEG *ffmpeg)
{
    FlushFileBuffers(ffmpeg->hPipeWrite);
    // FlushFileBuffers(ffmpeg->hPipeRead);

    CloseHandle(ffmpeg->hPipeWrite);
    // CloseHandle(ffmpeg->hPipeRead);

    DWORD result = WaitForSingleObject(
                       ffmpeg->hProcess,     // HANDLE hHandle,
                       INFINITE // DWORD  dwMilliseconds
                   );

    if (result == WAIT_FAILED) {
        fprintf(stderr, "ERROR: could not wait on child process: %s\n", GetLastErrorAsString());
        return;
    }

    DWORD exit_status;
    if (GetExitCodeProcess(ffmpeg->hProcess, &exit_status) == 0) {
        fprintf(stderr, "ERROR: could not get process exit code: %lu\n", GetLastError());
        return;
    }

    if (exit_status != 0) {
        fprintf(stderr, "ERROR: command exited with exit code %lu\n", exit_status);
        return;
    }

    CloseHandle(ffmpeg->hProcess);
}
#else
    #error "Unsupported OS"
#endif

#endif // FFMPEG_IMPLEMENTATION